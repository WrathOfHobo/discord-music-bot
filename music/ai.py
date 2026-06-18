"""Gemini:自然語言找歌、自動電台推薦、歌詞翻譯。未設金鑰時自動停用。"""
import asyncio
import json
import os

_API_KEY = os.getenv("GEMINI_API_KEY")
_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_client = None
_types = None

if _API_KEY:
    try:
        from google import genai
        from google.genai import types as _types
        _client = genai.Client(api_key=_API_KEY)
    except Exception as e:  # 套件沒裝或金鑰錯
        print(f"[ai] Gemini 初始化失敗,AI 功能停用: {e}")


def available() -> bool:
    return _client is not None


async def _generate(prompt: str, system: str, as_json: bool) -> str:
    def _call():
        cfg = _types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json" if as_json else "text/plain",
        )
        resp = _client.models.generate_content(model=_MODEL, contents=prompt, config=cfg)
        return resp.text or ""
    return await asyncio.get_running_loop().run_in_executor(None, _call)


async def find_songs(description: str, n: int = 5, history: list[str] | None = None) -> list[str]:
    if not _client:
        return []
    system = (
        "你是音樂推薦助手。根據使用者描述挑選最合適的歌曲。"
        f"只回傳 JSON 陣列,共 {n} 個元素,每個是字串 '歌手 - 歌名',不要任何其他文字。"
    )
    prompt = description
    if history:
        prompt += "\n\n最近播放過(延伸風格、避免重複):\n" + "\n".join(history)
    try:
        txt = await _generate(prompt, system, as_json=True)
        data = json.loads(txt)
        if isinstance(data, list):
            return [str(x) for x in data if x][:n]
    except Exception as e:
        print(f"[ai] find_songs 失敗: {e}")
    return []


async def translate_lyrics(lyrics: str) -> str:
    if not _client:
        return ""
    system = "你是歌詞翻譯。把使用者提供的歌詞翻成流暢的繁體中文,逐行對應,只回傳翻譯。"
    try:
        return await _generate(lyrics[:4000], system, as_json=False)
    except Exception as e:
        print(f"[ai] translate 失敗: {e}")
        return ""
