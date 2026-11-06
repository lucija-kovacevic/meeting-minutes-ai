"""
Instalacija meeting-minutes-ai (Windows).
  - virtualno okruzenje u %USERPROFILE%\\.meeting-minutes-ai\\venv (izvan OneDrivea)
  - Python paketi iz requirements.txt
  - modeli za prepoznavanje govornika (sherpa-onnx) u ./modeli
  - postavke.json i rjecnik.txt (ako ne postoje)
  - Claude skill 'zapisnik' u %USERPROFILE%\\.claude\\skills\\zapisnik

Pokreni preko instaliraj.bat ili: python instaliraj.py [--ime "Ana"] [--bez-pitanja]
"""
import argparse
import json
import os
import subprocess
import sys
import tarfile
import urllib.request
import venv
from pathlib import Path

BASE = Path(__file__).resolve().parent
# Namjerno izvan AppData: zapakirane aplikacije (npr. Claude desktop) preusmjeravaju
# pisanje u AppData u svoj privatni prostor, pa venv ne bi bio vidljiv iz Explorera.
APP = Path.home() / ".meeting-minutes-ai"
VENV = APP / "venv"
VPY = VENV / "Scripts" / "python.exe"
MODELI = BASE / "modeli"
SEG_URL = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/"
           "sherpa-onnx-pyannote-segmentation-3-0.tar.bz2")
EMB_URL = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/"
           "wespeaker_en_voxceleb_resnet34_LM.onnx")


def korak(t):
    print(f"\n== {t}")


def preuzmi(url, cilj: Path):
    print(f"  preuzimam {url.rsplit('/', 1)[-1]} ...")
    tmp = cilj.with_suffix(cilj.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.replace(cilj)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ime", help="tvoje ime (oznaka tvog mikrofona u transkriptu)")
    ap.add_argument("--bez-pitanja", action="store_true")
    a = ap.parse_args()

    if sys.version_info < (3, 10):
        sys.exit("Potreban je Python 3.10 ili noviji: https://www.python.org/downloads/")

    korak(f"Virtualno okruzenje: {VENV}")
    if not VPY.exists():
        venv.EnvBuilder(with_pip=True).create(VENV)
    korak("Instaliram pakete (prvi put moze potrajati nekoliko minuta)")
    subprocess.check_call([str(VPY), "-m", "pip", "install", "--disable-pip-version-check",
                           "-q", "-r", str(BASE / "requirements.txt")])

    korak("Modeli za prepoznavanje govornika")
    MODELI.mkdir(exist_ok=True)
    seg = MODELI / "sherpa-onnx-pyannote-segmentation-3-0" / "model.onnx"
    if not seg.exists():
        arh = MODELI / "segmentacija.tar.bz2"
        preuzmi(SEG_URL, arh)
        with tarfile.open(arh) as t:
            t.extractall(MODELI, filter="data")
        arh.unlink()
    emb = MODELI / "glasovi.onnx"
    if not emb.exists():
        preuzmi(EMB_URL, emb)
    print("  ok")

    korak("Postavke")
    pf = BASE / "postavke.json"
    post = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else {}
    ime = a.ime or post.get("ime")
    if not ime and not a.bez_pitanja:
        try:
            ime = input("  Tvoje ime (kako ce se oznacavati tvoj mikrofon): ").strip()
        except EOFError:
            ime = ""
    post["ime"] = ime or "Ja"
    post.setdefault("mapa_snimki", str(Path.home() / "Snimke sastanaka"))
    pf.write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ime: {post['ime']}, snimke: {post['mapa_snimki']}")
    rj = BASE / "rjecnik.txt"
    if not rj.exists():
        rj.write_text((BASE / "rjecnik.primjer.txt").read_text(encoding="utf-8"), encoding="utf-8")
        print("  napravljen rjecnik.txt - upisi u njega imena, organizacije i kratice")

    korak("Claude skill 'zapisnik'")
    tpl = (BASE / "skill" / "zapisnik" / "SKILL.md").read_text(encoding="utf-8")
    for k, v in {"{{MAPA}}": str(BASE), "{{SNIMKE}}": post["mapa_snimki"],
                 "{{PYTHON}}": str(VPY), "{{IME}}": post["ime"]}.items():
        tpl = tpl.replace(k, v)
    sd = Path.home() / ".claude" / "skills" / "zapisnik"
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "SKILL.md").write_text(tpl, encoding="utf-8")
    print(f"  {sd / 'SKILL.md'}")

    print("\nGotovo! Pokreni 'Snimi (HR).bat' ili 'Snimi (EN).bat' na pocetku sastanka.")


if __name__ == "__main__":
    main()
