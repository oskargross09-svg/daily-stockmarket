#!/usr/bin/env bash
# Einmalige Einrichtung pro (frischer) Maschine: Python-Pakete, Chromium, Piper-Stimme "Thorsten" (~60 MB, gecacht).
set -e
PIP="pip install -q --break-system-packages"
$PIP piper-tts playwright numpy scipy pillow 2>/dev/null || pip install -q piper-tts playwright numpy scipy pillow
python3 -m playwright install chromium >/dev/null 2>&1 || python3 -m playwright install --with-deps chromium
M="${DS_MODELS:-$HOME/.cache/daily-stockmarket}"
mkdir -p "$M"
if [ ! -s "$M/de-thorsten-low.onnx" ]; then
  curl -sSfL -o "$M/thorsten.tar.gz" https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-de-thorsten-low.tar.gz
  tar xzf "$M/thorsten.tar.gz" -C "$M" && rm "$M/thorsten.tar.gz"
fi
which ffmpeg >/dev/null || (sudo apt-get install -y -qq ffmpeg || apt-get install -y -qq ffmpeg)
python3 -c "import piper, playwright, numpy, scipy, PIL" && echo "setup ok"
