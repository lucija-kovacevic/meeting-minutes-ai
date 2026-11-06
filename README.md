# meeting-minutes-ai

Local, free meeting recorder + transcriber for **Windows** that also writes the minutes with **Claude**.
Works with any meeting app (Teams, Zoom, Google Meet…) — **no bot joins the call and you don't have to be the organizer**: it records what your computer plays and what your microphone hears.

*Hrvatski opis je niže.* 🇭🇷

## Features
- 🎙️ Records system audio (all outputs: speakers, headphones, Bluetooth) + your microphone
- 📝 Transcribes **locally** with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (`large-v3-turbo`) — nothing is uploaded
- 🗣️ Speaker labels: your mic is labeled with your name; other participants are separated by voice (`Govornik 1, 2…`) using [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx); speaker echo picked up by your mic is removed
- 🤖 Automatically writes structured minutes (summary, decisions, action items with owners & deadlines, open questions) via Claude Code, saved as `Zapisnik_<DATE>_<PARTNER>_<Topic>.md`
- 🌍 Croatian, English and other Whisper languages

## Requirements
- Windows 10/11
- Python 3.10+ ([python.org](https://www.python.org/downloads/), tick *Add python.exe to PATH*)
- ~2 GB disk (Whisper model downloads on first use)
- Optional, for automatic minutes: a Claude account plus [Claude Code](https://claude.com/claude-code) **or** the Claude desktop app (open its **Code** tab at least once so Claude Code gets downloaded). Without it you still get the transcript.

## Install
1. Download this repo (**Code → Download ZIP**) and unzip it anywhere
2. Double-click **`instaliraj.bat`** and enter your name when asked

This creates a virtual environment in `%USERPROFILE%\.meeting-minutes-ai`, downloads the speaker models, and installs the Claude skill `zapisnik`.

### About the Claude skill
- **You don't need to download it separately** — `instaliraj.bat` fills in your name and paths and installs it to `%USERPROFILE%\.claude\skills\zapisnik`.
- It works in **Claude Code** (and the **Code** tab of the Claude desktop app). That's what the automatic minutes use.
- In the regular Claude chat (claude.ai) personal skills are not picked up automatically. If you want to ask for minutes there too, zip the folder `%USERPROFILE%\.claude\skills\zapisnik` and upload it under *Settings → Capabilities → Skills*.
- Minutes use your own Claude account and quota.

## Use
1. At the start of a meeting double-click **`Snimi (HR).bat`**, **`Snimi (EN).bat`** or **`Snimi (automatski jezik).bat`**
2. Press **Enter** when the meeting ends
3. Optionally type the partner and topic (or press Enter and Claude will infer them)
4. Keep working — processing runs in the background on half of the CPU cores with low priority, so the laptop stays usable (it takes roughly 1–2× the meeting length). The minutes open automatically.

Other commands (`python` = `%USERPROFILE%\.meeting-minutes-ai\venv\Scripts\python.exe`):
```bash
python snimi.py --datoteka recording.mp4 --jezik en   # transcribe an existing recording
python snimi.py --zapisnik 2026-11-04_1721 --partner ACME --tema "Kick-off"
python snimi.py --bez-govornika                       # faster, no speaker separation
python snimi.py --puna-snaga                          # use all CPU cores (faster, laptop slows down)
python snimi.py --uredaji                             # list audio devices
```
Put names, organizations and abbreviations into `rjecnik.txt` to improve recognition.

## Privacy & legal
- Audio and transcripts stay on your computer. Only the transcript is sent to Claude if you use automatic minutes.
- **Always tell participants that you are recording/transcribing** — in the EU this is a GDPR requirement.
- `Sastanci/`, `postavke.json`, `rjecnik.txt` and audio files are git-ignored.

---

## 🇭🇷 Hrvatski

Lokalni, besplatni alat za snimanje i transkripciju sastanaka na **Windowsima** koji uz pomoć **Claudea** sam piše zapisnik. Radi s Teamsom, Zoomom, Google Meetom i drugima — **nikakav bot ne ulazi u sastanak i ne moraš biti organizator**: snima ono što računalo pušta i što čuje tvoj mikrofon.

**Instalacija:** preuzmi repo (*Code → Download ZIP*), raspakiraj i dvoklikni **`instaliraj.bat`**.

**Korištenje:** na početku sastanka dvoklik na **`Snimi (HR).bat`** / **`Snimi (EN).bat`** → na kraju **Enter** → upiši partnera i temu (ili Enter) → nastavi raditi (obrada ide u pozadini na pola procesora, pa laptop ne usporava; traje otprilike 1–2× trajanja sastanka). Zapisnik se sprema u `Sastanci\<DATUM>_<PARTNER>_<Tema>\` i otvara se sam.

Možeš i ručno u Claudeu: *„napravi zapisnik od zadnjeg sastanka"*.

**Claude i skill:** za automatski zapisnik treba Claude račun i Claude Code ili Claude desktop aplikacija (barem jednom otvori karticu **Code**). Skill `zapisnik` **ne treba posebno skidati**, jer ga `instaliraj.bat` sam postavi s tvojim imenom. Radi u Claude Codeu, odnosno kartici Code. Ako ga želiš i u običnom Claude chatu, zipaj mapu `%USERPROFILE%\.claude\skills\zapisnik` i učitaj je u *Settings → Capabilities → Skills*. Zapisnici troše tvoju Claude kvotu.

**Napomena:** obavezno reci sudionicima da snimaš (GDPR).

## Credits & licenses
Code: MIT (see `LICENSE`). Models are downloaded at install time and keep their own licenses: Whisper (MIT), [pyannote segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0) (MIT), WeSpeaker ResNet34 embedding via sherpa-onnx releases.
