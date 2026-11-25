# TikTok Creator Finder

Finds up to 100 TikTok creators who have **fewer than 5,000 followers**, **fewer than 13 posts**, and **at least 3 videos over 100,000 views**. Results go into `creators.csv`, which you can open in Excel or Google Sheets.

## How to run it

1. Install Python 3 from https://www.python.org/downloads/ (on Windows, tick **"Add Python to PATH"** during install).
2. Put your hashtags in `hashtags.txt`, one per line (no `#` needed).
3. Run it:
   - **Mac:** open Terminal, type `bash ` (with a space), drag `run.sh` into the window, press Enter.
   - **Windows:** double-click `run.bat`.

The first run sets everything up, which takes a few minutes. After that it starts right away.

A browser window will open and move by itself. **Leave it alone.** It's how the tool reads TikTok.

## Things to know
- **It's slow on purpose.** It waits a few seconds between requests so TikTok doesn't block it. Expect it to run for hours.
- **Stopping and continuing:** close the window or press Ctrl+C at any time. Run it again and it continues from where it stopped.
- **Starting over:** delete `progress.json`.
- **If it says TikTok is blocking it:** log in to tiktok.com in Chrome, press F12, open the *Application* tab, then *Cookies* and `https://www.tiktok.com`. Copy the value of `msToken`, paste it into a new file called `ms_token.txt` in this folder, and run again.
