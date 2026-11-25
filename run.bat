@echo off
REM Windows: sets everything up the first time, then runs the finder.
cd /d "%~dp0"
if not exist .venv (
  echo First-time setup, takes a few minutes...
  python -m venv .venv || (echo Please install Python 3 from python.org first & pause & exit /b 1)
  .venv\Scripts\pip install -q -r requirements.txt
  .venv\Scripts\python -m playwright install chromium
)
.venv\Scripts\python finder.py
pause
