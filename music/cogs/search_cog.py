"""搜尋:search(YouTube)/ scsearch(SoundCloud),回傳下拉選單供選擇。"""
import discord
from discord import app_commands
from discord.ext import commands

from .. import sources
from ..player import Track
from ..ui import SearchView
from .playback import connect


class SearchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _do_search(self, interaction: discord.Interaction, query: str, source: str):
        if not interaction.user.voice:
            await interaction.response.send_message("你要先加入語音頻道", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            entries = await sources.search(query, source=source, limit=5)
        except Exception as e:
            await interaction.followup.send(f"搜尋失敗:`{e}`")
            return
        if not entries:
            await interaction.followup.send("找不到結果")
            return

        async def on_pick(pick: discord.Interaction, entry):
            await pick.response.defer()
            player = await connect(pick)
            if player is None:
                await pick.followup.send("你要先加入語音頻道", ephemeral=True)
                return
            track = Track.from_search_entry(entry, pick.user)
            was_active = bool(player.current) or player.voice.is_playing() or player.voice.is_paused()
            player.queue.append(track)
            await player.ensure_playing()
            msg = f"➕ 已加入佇列:**{track.title}**" if was_active else f"▶️ 播放:**{track.title}**"
            await pick.edit_original_response(content=msg, embed=None, view=None)

        label = "YouTube" if source == "youtube" else "SoundCloud"
        await interaction.followup.send(f"🔎 {label} 搜尋「{query}」:", view=SearchView(entries, on_pick))

    @app_commands.command(description="搜尋 YouTube 並選擇")
    async def search(self, interaction: discord.Interaction, query: str):
        await self._do_search(interaction, query, "youtube")

    @app_commands.command(description="搜尋 SoundCloud 並選擇(YouTube 被擋時的備援)")
    async def scsearch(self, interaction: discord.Interaction, query: str):
        await self._do_search(interaction, query, "soundcloud")


async def setup(bot):
    await bot.add_cog(SearchCog(bot))
