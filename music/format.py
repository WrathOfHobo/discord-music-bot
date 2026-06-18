"""顯示用小工具:時間格式、進度條、時間字串解析。"""
import re


def fmt_duration(seconds) -> str:
    seconds = int(seconds or 0)
    if seconds <= 0:
        return "🔴 直播/未知"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def progress_bar(pos: int, total: int, length: int = 18) -> str:
    if not total:
        return "▬" * length
    pos = max(0, min(pos, total))
    filled = min(int(length * pos / total), length - 1)
    return "▬" * filled + "🔘" + "▬" * (length - filled - 1)


def parse_time(text: str):
    """'90' / '1:30' / '1:02:03' / '1h2m3s' -> 秒。失敗回 None。"""
    text = text.strip().lower()
    if not text:
        return None
    if ":" in text:
        try:
            parts = [int(p) for p in text.split(":")]
        except ValueError:
            return None
        sec = 0
        for p in parts:
            sec = sec * 60 + p
        return sec
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", text)
    if m and any(m.groups()):
        h, mn, s = (int(x) if x else 0 for x in m.groups())
        return h * 3600 + mn * 60 + s
    if text.isdigit():
        return int(text)
    return None


def parse_seek(text: str):
    """回傳 (mode, seconds):mode 為 'abs' 或 'rel'(相對含正負)。失敗回 None。"""
    text = text.strip()
    mode, sign = "abs", 1
    if text.startswith("+"):
        mode, text = "rel", text[1:]
    elif text.startswith("-"):
        mode, sign, text = "rel", -1, text[1:]
    val = parse_time(text)
    if val is None:
        return None
    return (mode, sign * val)
