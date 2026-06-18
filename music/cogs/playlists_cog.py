"""具名歌單:playlist_save / playlist_load / playlists / playlist_delete。"""
import discord
from discord import app_commands
from discord.ext import commands

from .. import db
from ..player import Track
from .playback import connect


class PlaylistsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="把目前佇列存成具名歌單")
    @app_commands.describe(name="歌單名稱")
    async def playlist_save(self, interaction: discord.Interaction, name: str):
        from ..player import get_player
        player = get_player(self.bot, interaction.guild)
        tracks = ([player.current.to_dict()] if player.current else []) + [t.to_dict() for t in player.queue]
        if not tracks:
            await interaction.response.send_message("目前沒有歌可存", ephemeral=True)
            return
        db.save_playlist(interaction.guild.id, interaction.user.id, name, tracks)
        await interaction.response.send_message(f"💾 已存歌單 **{name}**({len(tracks)} 首)")

    @app_commands.command(description="載入具名歌單到佇列")
    @app_commands.describe(name="歌單名稱")
    async def playlist_load(self, interaction: discord.Interaction, name: str):
        tracks = db.get_playlist(interaction.guild.id, name)
        if not tracks:
            await interaction.response.send_message(f"找不到歌單 **{name}**", ephemeral=True)
            return
        if not interaction.user.voice:
            await interaction.response.send_message("你要先加入語音頻道", ephemeral=True)
            return
        await interaction.response.defer()
        player = await connect(interaction)
        for d in tracks:
            player.queue.append(Track.from_dict(d, interaction.user))
        await player.ensure_playing()
        await interaction.followup.send(f"📂 已載入歌單 **{name}**({len(tracks)} 首)")

    @app_commands.command(description="列出所有歌單")
    async def playlists(self, interaction: discord.Interaction):
        rows = db.list_playlists(interaction.guild.id)
        if not rows:
            await interaction.response.send_message("還沒有任何歌單")
            return
        await interaction.response.send_message(
            "📚 歌單:\n" + "\n".join(f"• **{r['name']}** — {r['count']} 首" for r in rows)
        )

    @app_commands.command(description="刪除歌單")
    @app_commands.describe(name="歌單名稱")
    async def playlist_delete(self, interaction: discord.Interaction, name: str):
        ok = db.delete_playlist(interaction.guild.id, name)
        await interaction.response.send_message(
            f"🗑️ 已刪除 **{name}**" if ok else f"找不到 **{name}**", ephemeral=not ok
        )


async def setup(bot):
    await bot.add_cog(PlaylistsCog(bot))
