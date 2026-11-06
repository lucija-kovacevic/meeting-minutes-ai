"""
Snimanje sastanka (zvuk sustava + mikrofon) i lokalna transkripcija Whisperom.

Upotreba:
  python snimi.py                      # snimi pa transkribiraj (Enter = kraj snimanja)
  python snimi.py --jezik en           # forsiraj jezik (default: automatski)
  python snimi.py --datoteka x.m4a     # samo transkribiraj postojecu snimku
  python snimi.py --uredaji            # popis audio uredaja
  python snimi.py --bez-transkripcije  # samo snimi

Rezultat: transkript -> Sastanci/<datum_vrijeme>/transkript.txt (uz skriptu)
          audio      -> mapa_snimki iz postavke.json (default: %USERPROFILE%/Snimke sastanaka)
"""
import argparse
import datetime as dt
import json
import os
import sys
import threading
import time
import wave
from pathlib import Path

BASE = Path(__file__).resolve().parent


def _postavke():
    try:
        return json.loads((BASE / "postavke.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


POSTAVKE = _postavke()
SASTANCI = BASE / "Sastanci"                     # transkripti i zapisnici
SNIMKE = Path(os.path.expandvars(POSTAVKE.get("mapa_snimki") or str(Path.home() / "Snimke sastanaka")))
RJECNIK = BASE / "rjecnik.txt"


# ---------------------------------------------------------------- snimanje
class Snimac:
    """Snima jedan audio uredaj u WAV. Za loopback dopunjava tisinu
    (WASAPI loopback ne salje podatke dok nista ne svira)."""

    def __init__(self, pa, info, putanja, popuni_tisinu):
        import pyaudiowpatch as pyaudio
        self.rate = int(info["defaultSampleRate"])
        self.ch = max(1, min(2, int(info["maxInputChannels"])))
        self.sw = 2
        self.popuni = popuni_tisinu
        self.napisano = 0
        self.t0 = None
        self.lock = threading.Lock()
        self.wf = wave.open(str(putanja), "wb")
        self.wf.setnchannels(self.ch)
        self.wf.setsampwidth(self.sw)
        self.wf.setframerate(self.rate)
        self.ime = info["name"]
        self.stream = pa.open(
            format=pyaudio.paInt16, channels=self.ch, rate=self.rate,
            input=True, input_device_index=info["index"],
            frames_per_buffer=1024, stream_callback=self._cb,
        )

    def _tisina(self, frames):
        if frames > 0:
            self.wf.writeframes(b"\x00" * frames * self.ch * self.sw)
            self.napisano += frames

    def _cb(self, data, n, _ti, _st):
        import pyaudiowpatch as pyaudio
        with self.lock:
            sad = time.monotonic()
            if self.t0 is None:
                self.t0 = sad
            if self.popuni:
                ocekivano = int((sad - self.t0) * self.rate) - n
                if ocekivano - self.napisano > self.rate // 10:
                    self._tisina(ocekivano - self.napisano)
            self.wf.writeframes(data)
            self.napisano += n
        return (None, pyaudio.paContinue)

    def start(self, t0):
        self.t0 = t0
        self.stream.start_stream()

    def stop(self, t_kraj):
        self.stream.stop_stream()
        self.stream.close()
        with self.lock:
            if self.popuni:
                self._tisina(int((t_kraj - self.t0) * self.rate) - self.napisano)
            self.wf.close()


def uredaji(pa):
    """Svi izlazni uredaji (zvucnici, slusalice, Bluetooth...) + zadani mikrofon."""
    import pyaudiowpatch as pyaudio
    wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
    loops = list(pa.get_loopback_device_info_generator())
    if not loops:
        loops = [pa.get_default_wasapi_loopback()]
    mic = pa.get_device_info_by_index(wasapi["defaultInputDevice"]) \
        if wasapi["defaultInputDevice"] >= 0 else None
    return loops, mic


def _cekaj_enter(stop):
    try:
        input()
        stop.set()
    except EOFError:
        pass


def snimi(mapa: Path, trajanje=None):
    import pyaudiowpatch as pyaudio
    pa = pyaudio.PyAudio()
    try:
        loops, mic = uredaji(pa)
        snimaci = []
        for i, lp in enumerate(loops, 1):
            try:
                snimaci.append(Snimac(pa, lp, mapa / f"sustav{i}.wav", True))
            except Exception as e:
                print(f"  (preskacem {lp['name']}: {e})")
        if mic:
            snimaci.append(Snimac(pa, mic, mapa / "mikrofon.wav", False))
        for s in snimaci:
            print(f"  snimam: {s.ime}")
        t0 = time.monotonic()
        for s in snimaci:
            s.start(t0)
        print("\n● SNIMANJE U TIJEKU — pritisni Enter za kraj.\n")
        stop = threading.Event()
        threading.Thread(target=_cekaj_enter, args=(stop,), daemon=True).start()
        while not stop.is_set():
            if trajanje and time.monotonic() - t0 >= trajanje:
                break
            m, s_ = divmod(int(time.monotonic() - t0), 60)
            print(f"\r  {m:02d}:{s_:02d}", end="", flush=True)
            stop.wait(1)
        t_kraj = time.monotonic()
        for s in snimaci:
            s.stop(t_kraj)
        print("\n  Snimanje zavrseno.")
    finally:
        pa.terminate()


# ---------------------------------------------------------------- transkripcija
def ucitaj_mix(datoteke):
    import numpy as np
    from faster_whisper.audio import decode_audio
    zapisi = [decode_audio(str(f), sampling_rate=16000) for f in datoteke if f.exists()]
    zapisi = [z for z in zapisi if len(z)]
    if not zapisi:
        raise SystemExit("Nema audio podataka.")
    n = max(len(z) for z in zapisi)
    mix = np.zeros(n, dtype="float32")
    for z in zapisi:
        mix[: len(z)] += z
    vrh = float(np.abs(mix).max()) or 1.0
    return mix / max(vrh, 1.0) if vrh > 1.0 else mix


def hms(s):
    s = int(s)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


DRETVE = max(2, (os.cpu_count() or 4) // 2)   # pola jezgri - laptop ostaje upotrebljiv
PUNA_SNAGA = False


def stedljivo():
    """Obrada u pozadini: nizi prioritet (uz pola jezgri, vidi DRETVE)."""
    if os.name != "nt" or PUNA_SNAGA:
        return
    try:
        import ctypes
        from ctypes import wintypes
        k = ctypes.windll.kernel32
        k.GetCurrentProcess.restype = wintypes.HANDLE
        h = k.GetCurrentProcess()
        k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.SetPriorityClass(h, 0x00004000)  # BELOW_NORMAL_PRIORITY_CLASS
    except Exception:
        pass


MODELI = BASE / "modeli"
JA = POSTAVKE.get("ime") or "Ja"
BEZ_GOVORNIKA = False


def diariziraj(audio):
    """Tko kada govori (lokalno, sherpa-onnx). Vraca [(start, end, 'Govornik N')] ili None."""
    seg_m = MODELI / "sherpa-onnx-pyannote-segmentation-3-0" / "model.onnx"
    emb_m = MODELI / "glasovi.onnx"
    try:
        import sherpa_onnx
    except ImportError:
        return None
    if not (seg_m.exists() and emb_m.exists()):
        return None
    cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(seg_m)),
            num_threads=min(4, DRETVE)),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(emb_m), num_threads=min(4, DRETVE)),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=-1, threshold=0.6),
        min_duration_on=0.3, min_duration_off=0.5,
    )
    if not cfg.validate():
        return None
    print("  Prepoznajem govornike...")
    res = sherpa_onnx.OfflineSpeakerDiarization(cfg).process(audio).sort_by_start_time()
    imena = {}
    out = []
    for r in res:
        if r.speaker not in imena:
            imena[r.speaker] = f"Govornik {len(imena) + 1}"
        out.append((r.start, r.end, imena[r.speaker]))
    return out


def rijeci(model, audio, jezik, prompt, oznaka):
    """Whisper s vremenom za svaku rijec -> [(start, end, rijec)], jezik."""
    trajanje = len(audio) / 16000 or 1
    segs, info = model.transcribe(
        audio, language=jezik, vad_filter=True, beam_size=5, word_timestamps=True,
        initial_prompt=prompt or None, condition_on_previous_text=False,
    )
    out = []
    for seg in segs:
        for w in (seg.words or []):
            out.append((w.start, w.end, w.word))
        print(f"\r  {oznaka}: {min(100, seg.end / trajanje * 100):5.1f}%  ", end="", flush=True)
    print(f"\r  {oznaka}: 100.0%  ")
    return out, info.language


def govornik_za(ws, we, dijar, zadnji):
    """Govornik s najvecim vremenskim preklapanjem s rijecju; inace najblizi."""
    preklop = {}
    for s, e, g in dijar:
        o = min(we, e) - max(ws, s)
        if o > 0:
            preklop[g] = preklop.get(g, 0) + o
    if preklop:
        return max(preklop, key=preklop.get)
    t = (ws + we) / 2
    best, dist = None, 1e9
    for s, e, g in dijar:
        d = min(abs(t - s), abs(t - e))
        if d < dist:
            best, dist = g, d
    return best if dist <= 1.0 else (zadnji or best or "Govornik ?")


def grupiraj(rijeci_, oznake, pauza=1.5):
    """Spoji uzastopne rijeci istog govornika u izjave [(start, end, govornik, tekst)]."""
    izjave = []
    for (s, e, w), g in zip(rijeci_, oznake):
        if izjave and izjave[-1][2] == g and s - izjave[-1][1] <= pauza:
            izjave[-1][1] = e
            izjave[-1][3] += w
        else:
            izjave.append([s, e, g, w])
    return [(s, e, g, t.strip()) for s, e, g, t in izjave if t.strip()]


def je_jeka(izjava, ostale):
    """Mikrofon cesto uhvati zvuk iz zvucnika - takve izjave izbaci."""
    import difflib
    import re
    s, e, _, t = izjava
    norm = lambda x: re.sub(r"[^\w ]", "", x.lower()).strip()
    a = norm(t)
    if not a:
        return True
    b = norm(" ".join(o[3] for o in ostale if o[0] <= e + 1.5 and o[1] >= s - 1.5))
    if not b:
        return False
    m = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sum(bl.size for bl in m.get_matching_blocks()) / len(a) > 0.6


def transkribiraj(sustav, mikrofon, izlaz: Path, jezik, model_ime):
    """sustav: audio datoteke s glasovima ostalih; mikrofon: tvoja datoteka ili None."""
    from faster_whisper import WhisperModel
    stedljivo()
    nacin = "puna snaga" if PUNA_SNAGA else f"u pozadini, {DRETVE} jezgre"
    print(f"\nUcitavam model '{model_ime}' ({nacin})...")
    model = WhisperModel(model_ime, device="cpu", compute_type="int8",
                         cpu_threads=(os.cpu_count() or 4) if PUNA_SNAGA else DRETVE)
    prompt = RJECNIK.read_text(encoding="utf-8").strip() if RJECNIK.exists() else None
    t_start = time.time()

    audio = ucitaj_mix(sustav)
    trajanje = len(audio) / 16000
    w_ost, jez = rijeci(model, audio, jezik, prompt, "ostali" if mikrofon else "transkripcija")
    dijar = None if BEZ_GOVORNIKA else diariziraj(audio)
    oznake, zadnji = [], None
    for s, e, _ in w_ost:
        zadnji = govornik_za(s, e, dijar, zadnji) if dijar else "?"
        oznake.append(zadnji)
    izjave = grupiraj(w_ost, oznake)

    if mikrofon and Path(mikrofon).exists():
        a_mic = ucitaj_mix([Path(mikrofon)])
        trajanje = max(trajanje, len(a_mic) / 16000)
        w_mic, _ = rijeci(model, a_mic, jezik or jez, prompt, "mikrofon")
        moje = grupiraj(w_mic, [JA] * len(w_mic))
        prije = len(moje)
        moje = [m for m in moje if not je_jeka(m, izjave)]
        if prije - len(moje):
            print(f"  (izbaceno {prije - len(moje)} odjeka iz zvucnika)")
        izjave = sorted(izjave + moje, key=lambda x: x[0])

    sa_govornicima = bool(dijar) or bool(mikrofon)
    with open(izlaz, "w", encoding="utf-8") as f:
        f.write(f"# Transkript — {izlaz.parent.name}\n# jezik: {jez}, trajanje: {hms(trajanje)}\n")
        if sa_govornicima:
            f.write(f"# govornici: '{JA}' = tvoj mikrofon (pouzdano); 'Govornik N' = ostali, "
                    f"razlikovani automatski po glasu (mogu se zamijeniti ili spojiti)\n")
        f.write("\n")
        for s, e, g, t in izjave:
            f.write(f"[{hms(s)}] {g}: {t}\n" if sa_govornicima and g != "?" else f"[{hms(s)}] {t}\n")
    n = len({g for *_, g, _ in izjave if g.startswith("Govornik")})
    print(f"  Gotovo za {hms(time.time() - t_start)}" + (f" — prepoznato govornika: {n}" if dijar else ""))
    print(f"\nTranskript: {izlaz}")


# ---------------------------------------------------------------- zapisnik (Claude)
def nadji_claude():
    import shutil
    c = shutil.which("claude")
    if c:
        return c
    lad = Path(os.environ.get("LOCALAPPDATA", ""))
    kandidati = sorted(lad.glob("Claude-Data/*/claude-code/*/*/claude.exe"),
                       key=lambda p: p.stat().st_mtime)
    return str(kandidati[-1]) if kandidati else None


def pitaj(tekst):
    try:
        return input(tekst).strip()
    except EOFError:
        return ""


def cisto_ime(s):
    import re
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", s).strip(" .")
    return re.sub(r"\s+", " ", s)[:120]


def slobodno(putanja: Path):
    if not putanja.exists():
        return putanja
    i = 2
    while True:
        p = putanja.with_name(f"{putanja.name}_{i}")
        if not p.exists():
            return p
        i += 1


def napravi_zapisnik(mapa: Path, audio_mapa, partner="", tema=""):
    """Pozove Claude (skill 'zapisnik') da napise zapisnik, zatim preimenuje mape."""
    import subprocess
    claude = nadji_claude()
    if not claude:
        print("\n(Claude nije pronaden - zapisnik napravi rucno: 'napravi zapisnik od zadnjeg sastanka')")
        return
    transkript = mapa / "transkript.txt"
    datum = mapa.name[:10]
    upute = (
        f"Koristi skill 'zapisnik'. AUTOMATSKI NACIN: nista ne pitaj i nista ne preimenuj.\n"
        f"Transkript: {transkript}\nRjecnik: {RJECNIK}\nDatum sastanka: {datum}\n"
        f"Partner: {partner or '(prepoznaj iz transkripta; ako nije jasno: Nepoznato)'}\n"
        f"Tema: {tema or '(prepoznaj iz transkripta, 2-5 rijeci)'}\n"
        f"Zapisnik spremi u datoteku: {mapa / 'zapisnik.md'}\n"
        f"Na kraju odgovora ispisi TOCNO jedan redak oblika:\n"
        f"IME: {datum}_<PARTNER>_<Tema>"
    )
    print("\nClaude pise zapisnik...")
    try:
        r = subprocess.run(
            [claude, "-p", upute, "--allowedTools", "Read,Write,Skill",
             "--permission-mode", "acceptEdits", "--add-dir", str(BASE)],
            cwd=str(BASE), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=900,
        )
    except Exception as e:
        print(f"  Greska pri pozivu Claudea: {e}")
        return
    zap = mapa / "zapisnik.md"
    if r.returncode != 0 or not zap.exists():
        print("  Zapisnik nije napravljen.\n", (r.stderr or r.stdout)[-800:])
        return
    ime = ""
    for red in r.stdout.splitlines():
        if red.strip().upper().startswith("IME:"):
            ime = cisto_ime(red.split(":", 1)[1])
    if not ime:
        ime = cisto_ime(f"{datum}_{partner or 'Nepoznato'}_{tema or 'Sastanak'}")
    nova = slobodno(mapa.with_name(ime))
    zap.rename(mapa / f"Zapisnik_{nova.name}.md")
    mapa.rename(nova)
    if audio_mapa and Path(audio_mapa).exists():
        Path(audio_mapa).rename(slobodno(Path(audio_mapa).with_name(nova.name)))
    print(f"  Zapisnik: {nova / f'Zapisnik_{nova.name}.md'}")
    try:
        if not os.environ.get("ZAPISNIK_NE_OTVARAJ"):
            os.startfile(nova / f"Zapisnik_{nova.name}.md")
    except Exception:
        pass


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Snimi i transkribiraj sastanak")
    ap.add_argument("--jezik", default=None, help="hr, en ... (default: automatski)")
    ap.add_argument("--model", default="large-v3-turbo",
                    help="large-v3-turbo (default), large-v3 (tocniji, sporiji), medium, small")
    ap.add_argument("--datoteka", help="transkribiraj postojecu audio/video datoteku")
    ap.add_argument("--uredaji", action="store_true", help="prikazi audio uredaje")
    ap.add_argument("--bez-transkripcije", action="store_true")
    ap.add_argument("--trajanje", type=int, help="automatski stani nakon N sekundi")
    ap.add_argument("--bez-zapisnika", action="store_true", help="ne pozivaj Claude za zapisnik")
    ap.add_argument("--zapisnik", metavar="MAPA", help="samo napravi zapisnik za postojecu mapu u Sastanci")
    ap.add_argument("--partner", default="")
    ap.add_argument("--tema", default="")
    ap.add_argument("--bez-govornika", action="store_true",
                    help="brze: ne razlikuj ostale govornike (tvoj mikrofon se i dalje oznacava)")
    ap.add_argument("--puna-snaga", action="store_true",
                    help="obrada sa svim jezgrama i normalnim prioritetom (brze, ali usporava laptop)")
    a = ap.parse_args()
    global BEZ_GOVORNIKA, PUNA_SNAGA
    BEZ_GOVORNIKA = a.bez_govornika
    PUNA_SNAGA = a.puna_snaga

    if a.zapisnik:
        mapa = Path(a.zapisnik)
        if not mapa.is_absolute():
            mapa = SASTANCI / mapa
        napravi_zapisnik(mapa, SNIMKE / mapa.name, a.partner, a.tema)
        return

    if a.uredaji:
        import pyaudiowpatch as pyaudio
        pa = pyaudio.PyAudio()
        loops, mic = uredaji(pa)
        for lp in loops:
            print("Izlaz:       ", lp["name"])
        print("Mikrofon:    ", mic["name"] if mic else "(nema)")
        pa.terminate()
        return

    if a.datoteka:
        src = Path(a.datoteka).resolve()
        mapa = SASTANCI / f"{dt.datetime.now():%Y-%m-%d_%H%M}_{src.stem}"
        mapa.mkdir(parents=True, exist_ok=True)
        transkribiraj([src], None, mapa / "transkript.txt", a.jezik, a.model)
        if not a.bez_zapisnika:
            napravi_zapisnik(mapa, None, a.partner, a.tema)
        return

    oznaka = f"{dt.datetime.now():%Y-%m-%d_%H%M}"
    audio_mapa = SNIMKE / oznaka
    audio_mapa.mkdir(parents=True, exist_ok=True)
    mapa = SASTANCI / oznaka
    print(f"Audio: {audio_mapa}")
    snimi(audio_mapa, a.trajanje)
    if a.bez_transkripcije:
        return
    partner, tema = a.partner, a.tema
    if not a.bez_zapisnika and not a.trajanje:
        print("\nZa naziv zapisnika (Enter = AI prepozna iz razgovora):")
        partner = partner or pitaj("  Partner (kratica organizacije): ")
        tema = tema or pitaj("  Tema: ")
    mapa.mkdir(parents=True, exist_ok=True)
    transkribiraj(sorted(audio_mapa.glob("sustav*.wav")), audio_mapa / "mikrofon.wav",
                  mapa / "transkript.txt", a.jezik, a.model)
    if not a.bez_zapisnika:
        napravi_zapisnik(mapa, audio_mapa, partner, tema)


if __name__ == "__main__":
    try:
        main()
    except ModuleNotFoundError as e:
        print(f"\nNedostaje paket: {e.name}\nPython: {sys.executable}\n"
              "Pokreni instaliraj.bat (ili: pip install -r requirements.txt)")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)
