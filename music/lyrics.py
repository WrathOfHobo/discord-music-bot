"""歌詞:用 lrclib.net(免金鑰,可拿到純文字與同步歌詞)。"""
import aiohttp

_UA = "DiscordMusicBot (https://github.com/; personal use)"


async def get_lyrics(query: str):
    """以歌名/關鍵字搜尋,回傳 dict 或 None。"""
    async with aiohttp.ClientSession(headers={"User-Agent": _UA}) as s:
        try:
            async with s.get("https://lrclib.net/api/search", params={"q": query}, timeout=10) as r:
                if r.status != 200:
                    return None
                results = await r.json()
        except Exception:
            return None
    if not results:
        return None
    best = results[0]
    return {
        "title": best.get("trackName"),
        "artist": best.get("artistName"),
        "plain": best.get("plainLyrics"),
        "synced": best.get("syncedLyrics"),
    }
