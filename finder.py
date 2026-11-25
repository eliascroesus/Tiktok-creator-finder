"""TikTok creator finder.

Finds creators with: < MAX_FOLLOWERS followers, < MAX_POSTS posts,
and at least MIN_HIT_VIDEOS videos over MIN_VIEWS views.
Progress is saved in progress.json so a rerun continues where it stopped.
"""
import asyncio
import csv
import json
import os
import random
import sys
from pathlib import Path

from TikTokApi import TikTokApi

# ---- Settings (safe to change) ----
TARGET_CREATORS = 100
MAX_FOLLOWERS = 5000          # must have FEWER than this
MAX_POSTS = 13                # must have FEWER than this
MIN_VIEWS = 100_000           # a "hit" video has MORE than this
MIN_HIT_VIDEOS = 3
VIDEOS_PER_HASHTAG = 1000     # how many recent videos to try per hashtag
DELAY_RANGE = (2.0, 5.0)      # random pause (seconds) between requests
HEADLESS = os.getenv("HEADLESS", "0") == "1"  # 0 = show browser window (less blocking)

HERE = Path(__file__).parent
HASHTAGS_FILE = HERE / "hashtags.txt"
PROGRESS_FILE = HERE / "progress.json"
CSV_FILE = HERE / "creators.csv"
MS_TOKEN_FILE = HERE / "ms_token.txt"
CSV_FIELDS = ["username", "profile_link", "followers", "total_posts",
              "videos_over_100k", "top_video_views", "top_video_link"]


def log(msg):
    print(msg, flush=True)


async def pause():
    await asyncio.sleep(random.uniform(*DELAY_RANGE))


def load_progress():
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {"hashtags_done": [], "checked": [], "matches": []}


def save_progress(p):
    tmp = PROGRESS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(p, indent=1))
    tmp.replace(PROGRESS_FILE)
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(p["matches"])


def views(video_dict):
    return int((video_dict.get("stats") or {}).get("playCount") or 0)


async def check_creator(api, username):
    """Returns a result row if the creator matches, else None."""
    user = api.user(username=username)
    info = await user.info()
    await pause()
    ui = info.get("userInfo", {})
    stats = ui.get("stats", {})
    followers = int(stats.get("followerCount") or 0)
    posts = int(stats.get("videoCount") or 0)
    if followers >= MAX_FOLLOWERS or posts >= MAX_POSTS:
        return None
    sec_uid = (ui.get("user") or {}).get("secUid")
    if sec_uid:
        user = api.user(username=username, sec_uid=sec_uid)

    hits, top_views, top_id = 0, 0, None
    async for v in user.videos(count=MAX_POSTS + 5):
        d = v.as_dict
        n = views(d)
        if n > MIN_VIEWS:
            hits += 1
        if n > top_views:
            top_views, top_id = n, d.get("id")
    await pause()
    if hits < MIN_HIT_VIDEOS:
        return None
    return {
        "username": username,
        "profile_link": f"https://www.tiktok.com/@{username}",
        "followers": followers,
        "total_posts": posts,
        "videos_over_100k": hits,
        "top_video_views": top_views,
        "top_video_link": f"https://www.tiktok.com/@{username}/video/{top_id}" if top_id else "",
    }


async def main():
    if not HASHTAGS_FILE.exists():
        log("Can't find hashtags.txt. Put one hashtag per line in it and run again.")
        return
    hashtags = [h.strip().lstrip("#") for h in HASHTAGS_FILE.read_text().splitlines()]
    hashtags = [h for h in hashtags if h and not h.startswith("//")]
    ms_token = os.getenv("MS_TOKEN") or (
        MS_TOKEN_FILE.read_text().strip() if MS_TOKEN_FILE.exists() else None)

    p = load_progress()
    checked = set(p["checked"])
    if p["matches"]:
        log(f"Resuming: {len(checked)} creators already checked, {len(p['matches'])} matches so far.")
    if len(p["matches"]) >= TARGET_CREATORS:
        log("Already found enough creators. Delete progress.json to start over.")
        return

    async with TikTokApi() as api:
        log("Opening browser session...")
        await api.create_sessions(ms_tokens=[ms_token] if ms_token else None,
                                  num_sessions=1, sleep_after=3, headless=HEADLESS,
                                  executable_path=os.getenv("CHROME_PATH") or None)
        for tag in hashtags:
            if tag in p["hashtags_done"]:
                continue
            log(f"\n== Hashtag #{tag} ==")
            scanned = 0
            failed = False
            try:
                async for video in api.hashtag(name=tag).videos(count=VIDEOS_PER_HASHTAG):
                    scanned += 1
                    if scanned % 30 == 0:
                        await pause()
                    d = video.as_dict
                    if views(d) <= MIN_VIEWS:
                        continue
                    username = (d.get("author") or {}).get("uniqueId")
                    if not username or username in checked:
                        continue
                    # Quick pre-filter using stats included with the video (saves a request)
                    a = d.get("authorStats") or {}
                    if a and (int(a.get("followerCount") or 0) >= MAX_FOLLOWERS
                              or int(a.get("videoCount") or 0) >= MAX_POSTS):
                        checked.add(username)
                        p["checked"].append(username)
                        continue
                    try:
                        row = await check_creator(api, username)
                    except Exception as e:
                        log(f"  Couldn't check @{username} ({type(e).__name__}), skipping.")
                        row = None
                        await pause()
                    checked.add(username)
                    p["checked"].append(username)
                    if row:
                        p["matches"].append(row)
                        log(f"  MATCH: @{username} - {row['followers']} followers, "
                            f"{row['total_posts']} posts, {row['videos_over_100k']} videos over 100k")
                    save_progress(p)
                    if len(checked) % 10 == 0 or row:
                        log(f"Checked {len(checked)} creators, found {len(p['matches'])} matches")
                    if len(p["matches"]) >= TARGET_CREATORS:
                        log(f"\nDone! Found {TARGET_CREATORS} creators. See creators.csv")
                        return
            except Exception as e:
                failed = True
                log(f"  Problem reading #{tag} ({type(e).__name__}). Moving on.")
                if scanned == 0:
                    log("  TikTok may be blocking us. See README (ms_token tip). Will retry this hashtag next run.")
            log(f"  Finished #{tag}: looked at {scanned} videos.")
            if failed and scanned == 0:
                continue
            p["hashtags_done"].append(tag)
            save_progress(p)

    save_progress(p)
    log(f"\nHashtags ran out. Checked {len(checked)} creators, found {len(p['matches'])} matches. See creators.csv")
    log("Tip: add more hashtags to hashtags.txt and run again - it will continue.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped. Progress is saved - run again to continue.")
        sys.exit(0)
