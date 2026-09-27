import os
import glob
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
import yt_dlp

app = FastAPI(title="Fast YouTube Stream Extraction API")

# Async ThreadPool Executor for sub-second parallel CPU extraction
executor = ThreadPoolExecutor(max_workers=20)

COOKIES_DIR = "cookies"


class CookieRotator:
    def __init__(self, cookies_dir: str = COOKIES_DIR):
        self.cookies_dir = cookies_dir
        self._ensure_dir()

    def _ensure_dir(self):
        if not os.path.exists(self.cookies_dir):
            os.makedirs(self.cookies_dir, exist_ok=True)

    def get_valid_cookie_files(self) -> List[str]:
        if not os.path.exists(self.cookies_dir):
            return []
        files = glob.glob(os.path.join(self.cookies_dir, "*.txt"))
        # Filter out files ending with .bad or .bad.txt
        valid = [f for f in files if not f.endswith(".bad") and not f.endswith(".bad.txt")]
        return valid

    def get_cookie(self) -> Optional[str]:
        valid_files = self.get_valid_cookie_files()
        if not valid_files:
            return None
        return random.choice(valid_files)

    def mark_bad(self, cookie_file: Optional[str]):
        if cookie_file and os.path.exists(cookie_file):
            bad_path = cookie_file + ".bad"
            try:
                os.rename(cookie_file, bad_path)
            except Exception:
                pass


cookie_rotator = CookieRotator()


def extract_sync(url: str, cookie_file: Optional[str] = None) -> dict:
    ydl_opts = {
        "format": "bestaudio/best",
        "skip_download": True,
        "noplaylist": True,
        "extract_flat": False,
        "check_formats": False,
        "nocheckcertificate": True,
        "player_skip": ["webpage", "configs"],
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android"]
            }
        },
        "quiet": True,
        "no_warnings": True,
    }

    if cookie_file and os.path.exists(cookie_file):
        ydl_opts["cookiefile"] = cookie_file

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info


@app.get("/extract")
async def extract_stream(url: str = Query(..., description="YouTube video URL")):
    cookie_file = cookie_rotator.get_cookie()
    loop = asyncio.get_running_loop()

    try:
        info = await loop.run_in_executor(executor, extract_sync, url, cookie_file)
    except Exception as e:
        # Mark failing cookie as bad if one was used
        if cookie_file:
            cookie_rotator.mark_bad(cookie_file)
            # Retry once without cookie or with another cookie
            retry_cookie = cookie_rotator.get_cookie()
            try:
                info = await loop.run_in_executor(executor, extract_sync, url, retry_cookie)
            except Exception as retry_err:
                if retry_cookie:
                    cookie_rotator.mark_bad(retry_cookie)
                raise HTTPException(status_code=500, detail=f"Extraction failed: {str(retry_err)}")
        else:
            raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    if not info:
        raise HTTPException(status_code=404, detail="No media info found")

    # Determine stream URL and metadata
    stream_url = info.get("url")
    if not stream_url and "formats" in info:
        # Pick best audio format
        audio_formats = [f for f in info["formats"] if f.get("acodec") != "none" and f.get("vcodec") == "none"]
        if audio_formats:
            stream_url = audio_formats[-1].get("url")
        elif info["formats"]:
            stream_url = info["formats"][-1].get("url")

    return {
        "status": "success",
        "id": info.get("id"),
        "title": info.get("title"),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "stream_url": stream_url,
        "uploader": info.get("uploader"),
        "formats": [
            {
                "format_id": f.get("format_id"),
                "url": f.get("url"),
                "ext": f.get("ext"),
                "acodec": f.get("acodec"),
                "vcodec": f.get("vcodec"),
            }
            for f in info.get("formats", []) if f.get("url")
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
