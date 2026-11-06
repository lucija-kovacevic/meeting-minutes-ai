---
name: zapisnik
description: Piše zapisnik sastanka iz Whisper transkripta (alat meeting-minutes-ai). Koristi UVIJEK kad korisnik traži zapisnik, bilješke, sažetak ili zadatke sa sastanka, npr. "napravi zapisnik od zadnjeg sastanka", "zapisnik od jučer", "što smo dogovorili na sastanku", "minutes from the meeting". Također kad traži transkripciju postojeće snimke.
---

# Zapisnik sastanka

## Gdje su datoteke
- Alat i transkripti: `{{MAPA}}`
  - transkripti: `Sastanci\<YYYY-MM-DD_HHMM>\transkript.txt` (nakon obrade mapa se preimenuje u `<DATUM>_<PARTNER>_<Tema>`)
  - rječnik pojmova i imena: `rjecnik.txt`
- Audio snimke: `{{SNIMKE}}\<YYYY-MM-DD_HHMM>\`
- Python alata: `{{PYTHON}}`
- Korisnik (njegov mikrofon u transkriptu): **{{IME}}**

## Koraci
1. **Nađi transkript.** Ako korisnik ne kaže koji, uzmi najnoviju **neobrađenu** mapu u `Sastanci\` (ime oblika `YYYY-MM-DD_HHMM`, bez datoteke `Zapisnik_*.md`); ako takve nema, najnoviju po vremenu izmjene. Ako spomene dan ili temu, nađi mapu po datumu; ako je više kandidata, kratko pitaj koji.
   - Ako transkripta nema, ali postoji snimka, prvo transkribiraj (u pozadini, na pola procesora; traje otprilike 1–2× trajanja snimke):
     `"{{PYTHON}}" snimi.py --datoteka "<putanja>" [--jezik hr|en] --bez-zapisnika` (pokrenuti iz mape alata).
2. **Pročitaj cijeli transkript** i `rjecnik.txt`.
3. **Napiši zapisnik** po predlošku niže.
4. **Imenuj i spremi** (vidi "Imenovanje"):
   - spremi zapisnik kao `Zapisnik_<DATUM>_<PARTNER>_<Tema>.md` u mapu sastanka,
   - preimenuj mapu sastanka u `Sastanci\` u `<DATUM>_<PARTNER>_<Tema>`,
   - preimenuj i odgovarajuću audio mapu u `{{SNIMKE}}` u isto ime (ako postoji),
   - ako ciljno ime već postoji, dodaj sufiks `_2`, `_3`…
5. U odgovoru pokaži zapisnik i ponudi Word/Docs verziju ili nacrt maila sudionicima (ako korisnik ima skill za pisanje mailova u svom stilu, koristi ga; napravi samo **nacrt**, nikad ne šalji).

## Automatski način (poziv iz skripte snimi.py)
Ako upute kažu "AUTOMATSKI NACIN": ništa ne pitaj, ne preimenuj mape (to radi skripta), ne nudi Word/mail. Samo pročitaj transkript i rječnik, napiši zapisnik u zadanu datoteku i na kraju ispiši točno jedan redak `IME: <DATUM>_<PARTNER>_<Tema>` po pravilima imenovanja. Ako partner nije jasan, koristi `Nepoznato`.

## Imenovanje
Oblik: `<DATUM>_<PARTNER>_<Tema>`, npr. `2026-11-04_ACME_Deliverable D3.2` ili `2026-11-12_ACME-GLOBEX_Pilot site`.
- **DATUM**: `YYYY-MM-DD`, datum sastanka (iz imena izvorne mape).
- **PARTNER**: organizacija s kojom je sastanak, kratica VELIKIM slovima ako je kratica. Više partnera spoji crticom. Sastanak cijelog konzorcija → `Konzorcij`; samo vlastita organizacija → `Interno`.
  Prepoznaj iz transkripta i `rjecnik.txt`. **Ako nije jasno, pitaj korisnika prije spremanja** — ne pogađaj.
- **Tema**: 2–5 riječi, na jeziku zapisnika, početno veliko slovo, bez znakova `\ / : * ? " < > |`.
- Prije preimenovanja kratko navedi predloženo ime; ako korisnik sam zada partnera ili temu, koristi njegove.

## Važno o Whisper transkriptu
- **Oznake govornika** (redak `[hh:mm:ss] Govornik: tekst`):
  - `{{IME}}` = korisnikov mikrofon — pouzdano.
  - `Govornik 1, 2, …` = ostali, razlikovani automatski po glasu. Poveži ih s imenima samo kad je jasno iz konteksta (netko se predstavi ili ga oslove: "Ana, možeš li…" → sljedeći govornik je vjerojatno Ana). Inače ostavi "Govornik N" ili `[?]`.
  - Razdvajanje nije savršeno: kratke riječi na prijelazu mogu biti pripisane krivoj osobi, a ista osoba se ponekad podijeli na dva broja. Zaključuj iz cijelog toka razgovora.
  - Ako oznaka nema, ne pripisuj izjave osobama bez jasnog konteksta; zadatak bez nositelja označi `[?]`.
- Whisper griješi u imenima i kraticama: ispravi prema `rjecnik.txt` i zdravom razumu, ali ne izmišljaj.
- Ignoriraj "halucinacije" u tišini (npr. "Hvala na gledanju", "Titlovi…", "Thanks for watching").
- **Ništa ne izmišljaj.** Sve nesigurno označi s `[?]`.

## Jezik
Zapisnik piši na jeziku sastanka (`jezik:` u zaglavlju transkripta), osim ako korisnik traži drugačije.

## Predložak

```markdown
# Zapisnik: <PARTNER> – <tema sastanka>

**Datum:** <DD. MM. YYYY.>  ·  **Trajanje:** <hh:mm>  ·  **Partner:** <PARTNER>
**Sudionici:** <imena; "(pretpostavka)" ako nije sigurno>
**Zapisničar:** {{IME}}

## Sažetak
<3–5 rečenica: svrha sastanka i najvažniji ishodi>

## Teme i rasprava
### 1. <tema>
- <ključne točke>

## Zaključci i odluke
- <što je odlučeno>

## Zadaci
| # | Zadatak | Nositelj | Rok |
|---|---------|----------|-----|
| 1 | ... | ... | ... |

## Otvorena pitanja
- <što je ostalo nedorečeno>

## Sljedeći sastanak
<datum/termin ako je dogovoren, inače "nije dogovoren">
```

Engleska verzija: *Minutes, Date, Duration, Participants, Minutes taken by, Summary, Topics and discussion, Decisions, Action items (Task / Owner / Deadline), Open questions, Next meeting.*

Stil: sažeto, u natuknicama. Zadaci konkretni (glagol + što); relativne rokove ("do petka") pretvori u datum ako je jasno iz datuma sastanka.
