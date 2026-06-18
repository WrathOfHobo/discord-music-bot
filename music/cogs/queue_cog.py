"""佇列:queue(分頁)/ remove / shuffle。"""
import discord
from discord import app_commands
from discord.ext import commands

from ..player import get_player
from ..ui import QueueView


class QueueCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="顯示播放佇列")
    @app_commands.describe(page="頁碼(從 1 開始)")
    async def queue(self, interaction: discord.Interaction, page: int = 1):
        player = get_player(self.bot, interaction.guild)
        view = QueueView(player, page=max(0, page - 1))
        await interaction.response.send_message(embed=view.embed(), view=view)

    @app_commands.command(description="從佇列移除歌曲(序號或 ALL)")
    @app_commands.describe(target="要移除的序號,或 ALL 清空")
    async def remove(self, interaction: discord.Interaction, target: str):
        player = get_player(self.bot, interaction.guild)
        if target.strip().lower() == "all":
            n = len(player.queue)
            player.queue.clear()
            await interaction.response.send_message(f"🗑️ 已清空佇列({n} 首)")
            return
        if not target.strip().isdigit():
            await interaction.response.send_message("請給序號或 ALL", ephemeral=True)
            return
        idx = int(target) - 1
        if 0 <= idx < len(player.queue):
            t = player.queue.pop(idx)
            await interaction.response.send_message(f"🗑️ 已移除:**{t.title}**")
        else:
            await interaction.response.send_message("序號超出範圍", ephemeral=True)

    @app_commands.command(description="打亂佇列順序")
    async def shuffle(self, interaction: discord.Interaction):
        player = get_player(self.bot, interaction.guild)
        if len(player.queue) < 2:
            await interaction.response.send_message("佇列太短,不用打亂", ephemeral=True)
            return
        player.shuffle()
        await interaction.response.send_message("🔀 已打亂佇列")


async def setup(bot):
    await bot.add_cog(QueueCog(bot))
