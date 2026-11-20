# Daily Stockmarket

Automatische Produktion der YouTube Shorts von **Daily Stockmarket** – viermal täglich (06:00, 12:00, 18:00, 24:00 Uhr) die wichtigsten Börsen- und Politik-News, moderiert vom Börsen-Dachs.

Ablauf: Ein geplanter Claude-Lauf recherchiert, schreibt `stories/<datum>_<ausgabe>.json`, rendert das Video (`pipeline/make_video.py`) und übergibt es mit `pipeline/publish.py`. Der Workflow `.github/workflows/publish.yml` lädt es per YouTube Data API hoch; YouTube veröffentlicht es zur Sendezeit.

Details: `CLAUDE.md`.
