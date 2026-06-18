"""Gemini:find(自然語言找歌)/ autoplay(自動電台)。"""
import discord
from discord import app_commands
from discord.ext import commands

from .. import ai, sources
from ..player import get_player, Track
from .playback import connect


class AICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="用自然語言找歌(Gemini),例如:像 Radiohead 那種氛圍")
    @app_commands.describe(description="想聽什麼", count="要幾首(1-10)")
    async def find(self, interaction: discord.Interaction, description: str,
                   count: app_commands.Range[int, 1, 10] = 5):
        if not ai.available():
            await interaction.response.send_message("尚未設定 GEMINI_API_KEY,AI 找歌停用", ephemeral=True)
            return
        if not interaction.user.voice:
            await interaction.response.send_message("你要先加入語音頻道", ephemeral=True)
            return
        await interaction.response.defer()
        player = await connect(interaction)
        names = await ai.find_songs(description, count)
        if not names:
            await interaction.followup.send("Gemini 沒有回傳結果")
            return
        added = []
        for name in names:
            try:
                info = await sources.resolve(name)
                if info:
                    player.queue.append(Track.from_info(info, interaction.user))
                    added.append(name)
            except Exception:
                continue
        await player.ensure_playing()
        await interaction.followup.send(
            ("🎶 已加入:\n" + "\n".join(f"- {n}" for n in added)) if added else "找到歌名但都搜尋失敗"
        )

    @app_commands.command(description="自動電台:佇列播完時用 Gemini 接續推薦")
    @app_commands.describe(enable="開或關")
    async def autoplay(self, interaction: discord.Interaction, enable: bool):
        if enable and not ai.available():
            await interaction.response.send_message("尚未設定 GEMINI_API_KEY", ephemeral=True)
            return
        player = get_player(self.bot, interaction.guild)
        player.autoplay = enable
        if enable:
            async def provider(p):
                names = await ai.find_songs("根據最近播放的歌,推薦風格相近的歌曲", n=5, history=p.history)
                out = []
                for name in names:
                    try:
                        info = await sources.resolve(name)
                        if info:
                            out.append(Track.from_info(info, p.bot.user))
                    except Exception:
                        continue
                return out
            player.autoplay_provider = provider
        await interaction.response.send_message(f"📻 自動電台:{'開' if enable else '關'}")


async def setup(bot):
    await bot.add_cog(AICog(bot))
