# Daily Stockmarket – Produktions-Runbook

Daily Stockmarket ist ein deutschsprachiger YouTube-Shorts-Kanal: **viermal täglich** (06:00, 12:00, 18:00, 24:00 Uhr Schweizer Zeit)
die wichtigsten Börsen- und Politik-News in 45–60 Sekunden, moderiert vom Börsen-Dachs. Seriöser Ton, Schweizer Rechtschreibung.
Gestaltung und Ton folgen dem Designsystem „Daily Stockmarket“ (claude.ai-Artefakt https://claude.ai/artifact/4Gcz6stGfZVUkuLjdBmh5E);
alles davon ist in `pipeline/template/` und `pipeline/sound.py` schon umgesetzt – du schreibst nur die Story-JSON.

Ein geplanter Lauf produziert EINE Ausgabe von Anfang bis Ende, ohne jemanden zu fragen.

## 1. Einrichten (2 min)
```
cd <repo> && bash pipeline/setup.sh
```
Ausgabe bestimmen (Zeit in **Europe/Zurich**): Lauf zwischen 05:00–05:59 → `06`, 11:00–11:59 → `12`, 17:00–17:59 → `18`,
23:00–23:59 → `24`. Liegt die Zeit ausserhalb dieser Fenster, nimm die nächste kommende Ausgabe.
Datum = heutiges Datum in Europe/Zurich (die `24`-Ausgabe trägt das Datum des Tages, der um Mitternacht endet).
Story-Datei: `stories/<YYYY-MM-DD>_<06|12|18|24>.json`. Gibt es schon `videos/<gleicher Name>.json`, ist die Ausgabe fertig: aufhören.

## 2. Recherchieren
Suche im Web (mehrere Suchen, WebFetch für die Artikel) nach dem aktuellen Stand. Schwerpunkt je Ausgabe:
- **06 Morgen:** Schluss Wall Street (Dow, S&P 500, Nasdaq) von gestern Abend, Asien heute früh (Nikkei, Hang Seng), vorbörsliche Erwartung SMI/DAX.
- **12 Mittag:** SMI und DAX am Mittag, grösste Bewegungen bei Einzeltiteln (v. a. Schweizer Blue Chips), US-Futures, Termine des Nachmittags.
- **18 Abend:** Schluss SMI und DAX, Eröffnung Wall Street, Gewinner/Verlierer des Tages.
- **24 Nacht:** Schluss Wall Street, nachbörsliche Firmenzahlen, wichtigste Politik- und Notenbank-News des Tages.
- Immer prüfen: Devisen (EUR/CHF, USD/CHF), Gold, Öl (Brent), Bitcoin – für den Ticker.
- **Wochenende/Feiertag:** keine Kurse vom Tag. Dann Wochenbilanz (Schluss Fr), Krypto, Politik und Ausblick auf die kommende Woche; Quellen mit „Schluss Fr“ beschriften.
- Politik-News nur, wenn sie Märkte oder viele Menschen betreffen (Zölle, Zinsen, Wahlen, Budget, Sanktionen).

Faktenregeln: Jede Zahl aus einer zuverlässigen Quelle (SIX, Deutsche Börse/Xetra, NYSE, Nasdaq, Reuters, AWP, finanzen.ch, cash.ch, FuW, NZZ, Handelsblatt) und wenn möglich von einer zweiten bestätigt.
Exakte Werte, nie schätzen; widersprechen sich Quellen, den neueren Stand nehmen oder die Zahl weglassen. Unbestätigte Eilmeldungen weglassen.
Nicht dasselbe Hauptthema wie die vorige Ausgabe (neueste Datei in `stories/`), ausser es gibt Neues – dann das Neue sagen.

## 3. Story-JSON schreiben
Vollständiges Beispiel: `pipeline/examples/2026-11-20_06.json` – kopieren und anpassen.

```jsonc
{
  "date": "2026-11-20", "edition": "18",          // 06 | 12 | 18 | 24
  "mood": "down",                                 // Gesamtlage: up | down | flat | politik → Krawattenfarbe und Dachs-Stimmung
  "ticker": [["SMI", "14 721,8", -1.1], ["Gold", "3 561 $", -1.8], ...],   // 6–8 Einträge: Name, Wert (oder ""), Veränderung in %
  "say": {"Nasdaq": "Nasdäk"},                    // Aussprache-Korrekturen für die Stimme (gilt für alle Sätze)
  "scenes": [ 4–5 Szenen: 1 hook, 2–3 news, 1 fazit – siehe unten ],
  "title": "…",                                   // YouTube-Titel ≤ 90 Zeichen, sachlich, mit Datum: "… | Börse am Abend 20.11."
  "description": "…",                             // 2–3 Sätze: was passiert ist und warum es wichtig ist
  "tags": ["Börse", "SMI", "Dow Jones", "…"]      // 5–8
}
```
Szene: `{"type": "hook|news|fazit", "dir": "up|down|flat|politik", "headline": "…", "source": "**SIX** · Schluss Fr, 17:30 Uhr", "lines": [...], "objects": [...]}`
- `headline`: Satzschreibung, ≤ 44 Zeichen (max. 52), keine `!`/`?`, keine Emojis. Ein Schlüsselwort/eine Zahl mit `*Sternchen*` markieren (Akzentfarbe).
- `lines`: die gesprochenen Sätze, je `{"cap": "Untertitel", "tts": "Sprechtext"}`. `tts` nur nötig, wenn Zahlen/Namen anders gesprochen werden:
  Zahlen im `tts` als Wörter („zwei Komma zwei Prozent“, „fünfzigtausend“), Abkürzungen buchstabiert („S M I“, „K I“).
- `objects` (das erste erscheint mit dem ersten Satz, jedes weitere mit Satz Nr. `at` und ersetzt das vorige):
  - `quote` (Kurs-Karte): `{"kind": "quote", "at": 0, "name": "SMI", "sub": "Swiss Market Index", "from": Vortag, "to": aktuell, "dec": 1, "pct": -1.1, "abs": -164.28}`
    Optional `"unit": "$"`, `"absUnit": "$"`, `"absDec"`, `"countLine"` (Satz, in dem gezählt wird), `"countDelay"` (Sekunden nach Satzbeginn, Standard 0,9).
  - `bars` (Balkenvergleich, 2–4 Zeilen): `{"kind": "bars", "at": 1, "title": "Leitindizes", "rows": [["SMI", -1.10], ["DAX", -1.06]]}`
  - `kennzahl` (die eine grosse Zahl): `{"kind": "kennzahl", "value": -2.2, "dec": 1, "unit": "%", "sign": true, "color": "down", "label": "**Dow Jones** · Schluss Do"}` (`color`: up | down | ink; max. ~7 Zeichen)
  - `statement` (nur Politik, `dir: "politik"`): `{"kind": "statement", "quote": "„Wörtliches Zitat, max. 15 Wörter.“", "who": "Name", "role": "Funktion"}`
- `hook`: 1 Satz + Kennzahl der wichtigsten Bewegung. `news`: 2–3 Sätze + Karte/Balken/Zitat. `fazit`: 1 Satz + 1 Kennzahl.
- Das Outro („Nächstes Update um …“, Abo) wird automatisch angehängt.

Schreibregeln: Nachrichtenton, dritte Person, Präsens, kurze Hauptsätze, Fakten zuerst („Der SMI schliesst 1,2 Prozent höher.“).
**ss statt ß.** Keine Kauf-/Verkaufsempfehlung, keine wertenden Adjektive („krass“, „Crash“ nur, wenn Quellen es so nennen).
Personen nur mit Name + Funktion, Zitate wörtlich. Zahlenformat: Komma als Dezimaltrenner, Leerzeichen als Tausendertrenner („14 721,8“),
Prozent mit Leerzeichen („−1,1 %“); Indizes 1 Nachkommastelle, Prozent 1, Rohstoffe/Krypto 2, Devisen 4.
Quellenzeile konkret („**SIX** · Schluss Fr, 17:30 Uhr“), nie „Medienberichte“.
Sprechtext gesamt **95–130 Wörter** → 45–60 s (das Skript warnt).

## 4. Layout prüfen
```
python3 pipeline/make_video.py stories/<name>.json --stills
```
Alle ERROR/WARNING beheben. Dann **`build/<name>/sheet.jpg` ansehen** (Read-Tool): nichts überlappt oder ist abgeschnitten,
Headlines max. 2 Zeilen, Kennzahl nicht über dem Dachs, Zahlen stimmen mit der Recherche. JSON korrigieren und wiederholen.

## 5. Rendern und veröffentlichen
```
python3 pipeline/publish.py stories/<name>.json
```
Rendert das MP4 (~2 min), legt es auf den Branch `media`, pusht `stories/` + `videos/<name>.json`; der Workflow
`.github/workflows/publish.yml` lädt es auf YouTube hoch und YouTube veröffentlicht es selbst zur Sendezeit
(bei weniger als 10 Minuten bis zur Sendezeit sofort). Das Skript wartet auf das Ergebnis.
- `RESULT: OK` → fertig. Abschluss in 2 Zeilen (Hauptthema + Sendezeit).
- `RESULT: FAILED` / `UNKNOWN` oder ein Schritt, den du nicht lösen kannst → einmal wiederholen (`--no-render`, wenn das MP4 schon da ist);
  klappt es dann nicht, dem Nutzer eine Push-Benachrichtigung (PushNotification-Tool) auf Deutsch senden: was fehlgeschlagen ist und dass die Ausgabe fehlt.

Nie etwas anderes veröffentlichen, nie Videos löschen, nie Workflows oder Secrets während eines geplanten Laufs ändern.

## Repo-Übersicht
- `pipeline/make_video.py` – Story → MP4 (Stimme Piper „Thorsten“, Timeline, Playwright-Rendering, Mix) · `pipeline/sound.py` – Musikbett + Soundeffekte
- `pipeline/template/` – HTML-Vorlage, Tokens, Komponenten-CSS, Schriften, Dachs-Rig, Logo (aus dem Designsystem)
- `pipeline/publish.py` – Übergabe an GitHub · `upload_youtube.py` – YouTube Data API (Secrets `CLIENT_ID`, `CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`)
- `stories/` – eine JSON pro Ausgabe · `videos/` – Upload-Aufträge (lösen `publish.yml` aus)
- Branch `media` – die MP4-Dateien (wöchentlich aufgeräumt) · Branch `bot-logs` – Ergebnisse des Upload-Workflows
