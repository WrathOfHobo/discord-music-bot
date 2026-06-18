"""歌詞:lyrics(可選 Gemini 翻譯)。"""
import discord
from discord import app_commands
from discord.ext import commands

from .. import ai
from .. import lyrics as lyrics_mod
from ..player import get_player


def _split(text: str, size: int) -> list[str]:
    out, cur = [], ""
    for line in text.splitlines():
        if len(cur) + len(line) + 1 > size:
            out.append(cur)
            cur = ""
        cur += line + "\n"
    if cur:
        out.append(cur)
    return out or [""]


class LyricsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="顯示歌詞(不填則用目前播放的歌)")
    @app_commands.describe(song="歌名/關鍵字", translate="用 Gemini 翻成中文")
    async def lyrics(self, interaction: discord.Interaction, song: str | None = None, translate: bool = False):
        if not song:
            player = get_player(self.bot, interaction.guild)
            if player.current:
                song = player.current.title
        if not song:
            await interaction.response.send_message("請給歌名,或先播一首歌", ephemeral=True)
            return
        await interaction.response.defer()
        data = await lyrics_mod.get_lyrics(song)
        if not data or not data.get("plain"):
            await interaction.followup.send(f"找不到「{song}」的歌詞")
            return
        text = data["plain"]
        if translate and ai.available():
            zh = await ai.translate_lyrics(text)
            if zh:
                text = zh
        header = f"🎤 **{data.get('artist', '')} - {data.get('title', song)}**"
        chunks = _split(text, 3800)
        await interaction.followup.send(f"{header}\n```\n{chunks[0]}\n```")
        for c in chunks[1:4]:
            await interaction.followup.send(f"```\n{c}\n```")


async def setup(bot):
    await bot.add_cog(LyricsCog(bot))
