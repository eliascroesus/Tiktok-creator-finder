#!/bin/bash
# Mac/Linux: sets everything up the first time, then runs the finder.
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "First-time setup (takes a few minutes)..."
  python3 -m venv .venv || { echo "Please install Python 3 from python.org first."; exit 1; }
  .venv/bin/pip install -q -r requirements.txt
  .venv/bin/python -m playwright install chromium
fi
.venv/bin/python finder.py
