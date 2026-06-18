"""Spotify 連結匯入(歌曲/歌單/專輯)→ 轉成歌名到 YouTube 搜尋排入。"""
import discord
from discord import app_commands
from discord.ext import commands

from .. import sources, spotify
from ..player import Track
from .playback import connect


class SpotifyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="從 Spotify 連結匯入(歌曲/歌單/專輯)")
    @app_commands.describe(url="Spotify 連結")
    async def spotify(self, interaction: discord.Interaction, url: str):
        if not spotify.available():
            await interaction.response.send_message(
                "尚未設定 SPOTIPY_CLIENT_ID / SECRET,Spotify 匯入停用", ephemeral=True
            )
            return
        if not interaction.user.voice:
            await interaction.response.send_message("你要先加入語音頻道", ephemeral=True)
            return
        await interaction.response.defer()
        names = await spotify.parse(url)
        if not names:
            await interaction.followup.send("無法從這個連結取得歌曲")
            return
        player = await connect(interaction)
        added = 0
        for name in names:
            try:
                info = await sources.resolve(name)
                if info:
                    player.queue.append(Track.from_info(info, interaction.user))
                    added += 1
            except Exception:
                continue
        await player.ensure_playing()
        await interaction.followup.send(f"🟢 從 Spotify 匯入 {added}/{len(names)} 首")


async def setup(bot):
    await bot.add_cog(SpotifyCog(bot))
