"""Spotify 連結匯入:讀取曲目 metadata 轉成 '歌手 - 歌名' 搜尋字串。
Spotify 本身有 DRM 無法直接播放,這裡只取歌名再到 YouTube 搜尋。
需設定 SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET。
"""
import asyncio
import os

_CID = os.getenv("SPOTIPY_CLIENT_ID")
_CS = os.getenv("SPOTIPY_CLIENT_SECRET")
_sp = None

if _CID and _CS:
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials
        _sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=_CID, client_secret=_CS))
    except Exception as e:
        print(f"[spotify] 初始化失敗,Spotify 功能停用: {e}")


def available() -> bool:
    return _sp is not None


def _names(query_list) -> list[str]:
    out = []
    for t in query_list:
        if not t:
            continue
        artists = ", ".join(a["name"] for a in t.get("artists", []))
        name = t.get("name", "")
        if name:
            out.append(f"{artists} - {name}" if artists else name)
    return out


def _parse(url: str) -> list[str]:
    if "track" in url:
        return _names([_sp.track(url)])
    if "playlist" in url:
        items = _sp.playlist_items(url, limit=100).get("items", [])
        return _names([i.get("track") for i in items])
    if "album" in url:
        items = _sp.album_tracks(url, limit=50).get("items", [])
        return _names(items)
    return []


async def parse(url: str) -> list[str]:
    if not _sp:
        return []
    return await asyncio.get_running_loop().run_in_executor(None, lambda: _parse(url))
