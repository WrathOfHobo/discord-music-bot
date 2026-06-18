"""yt-dlp 抽取封裝:解析、播放時取串流、搜尋(YouTube / SoundCloud)。

設計重點:佇列裡只存網頁網址 (webpage_url),真正的串流網址在「要播的當下」
才用 get_stream() 解析,避免排很久之後 googlevideo 連結過期。
"""
import asyncio
import os

import yt_dlp

_ROOT = os.path.dirname(os.path.dirname(__file__))
_COOKIES = os.path.join(_ROOT, "cookies.txt")

_BASE = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "source_address": "0.0.0.0",
}


def _opts(**extra):
    o = dict(_BASE)
    if os.path.exists(_COOKIES):
        o["cookiefile"] = _COOKIES
    elif os.getenv("COOKIES_FROM_BROWSER"):
        o["cookiesfrombrowser"] = (os.getenv("COOKIES_FROM_BROWSER"),)
    o.update(extra)
    return o


def cookies_status() -> str:
    if os.path.exists(_COOKIES):
        return "cookies.txt"
    if os.getenv("COOKIES_FROM_BROWSER"):
        return f"browser:{os.getenv('COOKIES_FROM_BROWSER')}"
    return "none"


def _extract(query, **opts):
    with yt_dlp.YoutubeDL(_opts(**opts)) as ydl:
        return ydl.extract_info(query, download=False)


async def resolve(query: str) -> dict:
    """完整解析網址或關鍵字(關鍵字取第一筆搜尋結果)。"""
    loop = asyncio.get_running_loop()
    extra = {} if query.startswith("http") else {"default_search": "ytsearch"}
    info = await loop.run_in_executor(None, lambda: _extract(query, **extra))
    if info and "entries" in info:
        info = info["entries"][0]
    return info


async def get_stream(webpage_url: str):
    """播放當下解析串流網址,回傳 (stream_url, duration秒)。"""
    loop = asyncio.get_running_loop()
    info = await loop.run_in_executor(None, lambda: _extract(webpage_url))
    if info and "entries" in info:
        info = info["entries"][0]
    return info["url"], int(info.get("duration") or 0)


async def search(query: str, source: str = "youtube", limit: int = 5) -> list[dict]:
    """搜尋並回傳精簡候選清單。source: 'youtube' | 'soundcloud'。"""
    prefix = "scsearch" if source == "soundcloud" else "ytsearch"
    loop = asyncio.get_running_loop()
    info = await loop.run_in_executor(
        None,
        lambda: _extract(f"{prefix}{limit}:{query}", extract_flat="in_playlist"),
    )
    return (info or {}).get("entries", []) or []


def is_playlist_url(query: str) -> bool:
    """是否為 YouTube(或其他)播放清單網址。"""
    return query.startswith("http") and ("list=" in query or "/playlist" in query)


async def resolve_playlist(url: str):
    """展開整張清單(flat 抽取,快;不設上限)。回傳 (清單標題, entries)。"""
    loop = asyncio.get_running_loop()
    info = await loop.run_in_executor(
        None, lambda: _extract(url, noplaylist=False, extract_flat="in_playlist")
    )
    entries = [e for e in (info or {}).get("entries", []) if e]
    return (info or {}).get("title") or "播放清單", entries
