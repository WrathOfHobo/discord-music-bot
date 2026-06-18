"""每個伺服器一個 GuildPlayer:管理佇列、目前曲目、播放/循環/seek/音量/自動電台。"""
import asyncio
import random
import time
from dataclasses import dataclass
from enum import Enum

import discord

from . import sources

_FF_BEFORE = (
    "-reconnect 1 -reconnect_streamed 1 -reconnect_on_network_error 1 "
    "-reconnect_delay_max 5"
)
_FF_OPTS = "-vn"


class LoopMode(Enum):
    OFF = 0
    TRACK = 1
    QUEUE = 2


def _source_of(info) -> str:
    key = (info.get("extractor_key") or info.get("ie_key") or info.get("extractor") or "").lower()
    return "soundcloud" if "soundcloud" in key else "youtube"


@dataclass
class Track:
    title: str
    webpage_url: str
    duration: int
    requester_id: int
    requester_name: str
    source: str = "youtube"
    thumbnail: str | None = None

    @classmethod
    def from_info(cls, info, requester):
        return cls(
            title=info.get("title") or "未知曲目",
            webpage_url=info.get("webpage_url") or info.get("url"),
            duration=int(info.get("duration") or 0),
            requester_id=requester.id,
            requester_name=getattr(requester, "display_name", str(requester)),
            source=_source_of(info),
            thumbnail=info.get("thumbnail"),
        )

    @classmethod
    def from_search_entry(cls, e, requester):
        url = e.get("webpage_url") or e.get("url")
        if url and not url.startswith("http") and (e.get("ie_key") or "").lower().startswith("youtube"):
            url = f"https://www.youtube.com/watch?v={url}"
        return cls(
            title=e.get("title") or "未知曲目",
            webpage_url=url,
            duration=int(e.get("duration") or 0),
            requester_id=requester.id,
            requester_name=getattr(requester, "display_name", str(requester)),
            source=_source_of(e),
            thumbnail=e.get("thumbnail"),
        )

    @classmethod
    def from_dict(cls, d, requester):
        return cls(
            title=d["title"], webpage_url=d["webpage_url"], duration=int(d.get("duration") or 0),
            requester_id=requester.id, requester_name=getattr(requester, "display_name", str(requester)),
            source=d.get("source", "youtube"), thumbnail=d.get("thumbnail"),
        )

    def to_dict(self):
        return {"title": self.title, "webpage_url": self.webpage_url,
                "duration": self.duration, "source": self.source, "thumbnail": self.thumbnail}


class GuildPlayer:
    def __init__(self, bot, guild_id):
        self.bot = bot
        self.guild_id = guild_id
        self.queue: list[Track] = []
        self.current: Track | None = None
        self.voice: discord.VoiceClient | None = None
        self.loop_mode = LoopMode.OFF
        self.volume = 0.5
        self.votes: set[int] = set()
        self.history: list[str] = []
        self.autoplay = False
        self.autoplay_provider = None  # async callable(player) -> list[Track]
        self.idle_ticks = 0
        # 進度追蹤
        self._start = 0.0
        self._paused_at: float | None = None
        self._seeking = False
        self._skip = False
        self._retries = 0

    # ---- 進度 ----
    def _begin_progress(self, position: int):
        self._start = time.monotonic() - position
        self._paused_at = None

    @property
    def position(self) -> int:
        if not self.current:
            return 0
        ref = self._paused_at if self._paused_at is not None else time.monotonic()
        return max(0, int(ref - self._start))

    # ---- 播放核心 ----
    async def play_track(self, track: Track, position: int = 0):
        stream_url, duration = await sources.get_stream(track.webpage_url)
        if duration and not track.duration:
            track.duration = duration
        before = (f"-ss {position} " if position > 0 else "") + _FF_BEFORE
        audio = discord.FFmpegPCMAudio(stream_url, before_options=before, options=_FF_OPTS)
        source = discord.PCMVolumeTransformer(audio, volume=self.volume)
        self.current = track
        self.votes.clear()
        self._begin_progress(position)
        self.voice.play(source, after=self._after)

    def _after(self, error):
        if error:
            print(f"[播放錯誤] guild={self.guild_id}: {error}")
        fut = asyncio.run_coroutine_threadsafe(self._advance(), self.bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f"[advance 錯誤] {e}")

    async def _advance(self):
        if self._seeking:
            return
        skip = self._skip
        self._skip = False
        # 中途中斷自動續播:非人為跳過、歌曲遠未播完 → 從中斷點接著播(上限 3 次)
        if not skip and self.current and self.current.duration:
            pos = self.position
            if pos < self.current.duration - 10 and self._retries < 3:
                self._retries += 1
                print(f"[續播] 中途中斷,從 {pos}s 接續(第 {self._retries}/3 次)")
                try:
                    await self.play_track(self.current, pos)
                    return
                except Exception as e:
                    print(f"[續播失敗] {e}")
        self._retries = 0
        if not skip and self.loop_mode == LoopMode.TRACK and self.current:
            await self.play_track(self.current)
            return
        if self.loop_mode == LoopMode.QUEUE and self.current:
            self.queue.append(self.current)
        await self._play_next()

    async def _play_next(self):
        self._retries = 0
        if not self.queue and self.autoplay and self.autoplay_provider:
            try:
                self.queue.extend(await self.autoplay_provider(self))
            except Exception as e:
                print(f"[autoplay 錯誤] {e}")
        if not self.queue:
            self.current = None
            return
        track = self.queue.pop(0)
        self.history.append(track.title)
        self.history = self.history[-20:]
        await self.play_track(track)

    async def ensure_playing(self):
        if self.voice and not self.voice.is_playing() and not self.voice.is_paused() and self.current is None:
            await self._play_next()

    # ---- 控制 ----
    def pause(self):
        if self.voice and self.voice.is_playing():
            self.voice.pause()
            self._paused_at = time.monotonic()
            return True
        return False

    def resume(self):
        if self.voice and self.voice.is_paused():
            if self._paused_at is not None:
                self._start += time.monotonic() - self._paused_at
                self._paused_at = None
            self.voice.resume()
            return True
        return False

    async def skip(self):
        self._skip = True
        if self.voice:
            self.voice.stop()

    async def stop(self):
        self.queue.clear()
        self.loop_mode = LoopMode.OFF
        self.autoplay = False
        self._skip = True
        self.current = None
        if self.voice:
            self.voice.stop()

    def shuffle(self):
        random.shuffle(self.queue)

    def set_volume(self, v: float):
        self.volume = max(0.0, min(v, 2.0))
        if self.voice and isinstance(self.voice.source, discord.PCMVolumeTransformer):
            self.voice.source.volume = self.volume

    async def seek(self, position: int):
        if not self.current:
            return False
        track = self.current
        position = max(0, position)
        self._seeking = True
        if self.voice and (self.voice.is_playing() or self.voice.is_paused()):
            self.voice.stop()
        for _ in range(60):
            if not self.voice or not self.voice.is_playing():
                break
            await asyncio.sleep(0.05)
        self._seeking = False
        await self.play_track(track, position)
        return True


def get_player(bot, guild) -> GuildPlayer:
    p = bot.players.get(guild.id)
    if p is None:
        p = GuildPlayer(bot, guild.id)
        bot.players[guild.id] = p
    return p
