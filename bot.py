"""Discord YouTube 音樂機器人 — 進入點。載入各 cog 並啟動。"""
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from music import db, sources

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

INITIAL_EXTENSIONS = [
    "music.cogs.playback",
    "music.cogs.queue_cog",
    "music.cogs.search_cog",
    "music.cogs.lyrics_cog",
    "music.cogs.ai_cog",
    "music.cogs.playlists_cog",
    "music.cogs.spotify_cog",
]


class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.players: dict[int, object] = {}

    async def setup_hook(self):
        db.init()
        for ext in INITIAL_EXTENSIONS:
            try:
                await self.load_extension(ext)
            except Exception as e:
                print(f"[載入失敗] {ext}: {e}")
        dev_guild = os.getenv("DEV_GUILD_ID")
        if dev_guild:  # 同步到單一伺服器,指令即時更新(開發/測試用)
            g = discord.Object(id=int(dev_guild))
            self.tree.copy_global_to(guild=g)
            synced = await self.tree.sync(guild=g)
            print(f"已同步 {len(synced)} 個指令到伺服器 {dev_guild}")
        else:  # 全域同步,新指令可能要幾分鐘到一小時才在每個伺服器出現
            synced = await self.tree.sync()
            print(f"已全域同步 {len(synced)} 個指令")

    async def on_ready(self):
        print(f"已登入:{self.user} | cookies={sources.cookies_status()}")


bot = MusicBot()


@bot.tree.error
async def _on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, discord.app_commands.CommandInvokeError):
        error = error.original
    # 互動逾時(語音不穩或當下卡頓時常見):已無法回覆,只記錄
    if isinstance(error, discord.NotFound) and getattr(error, "code", None) == 10062:
        print("[指令] 互動逾時(Unknown interaction);通常是語音不穩或當下卡頓")
        return
    print(f"[指令錯誤] {type(error).__name__}: {error}")
    try:
        if interaction.response.is_done():
            await interaction.followup.send(f"⚠️ 指令出錯:`{error}`", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ 指令出錯:`{error}`", ephemeral=True)
    except Exception:
        pass


if __name__ == "__main__":
    if not TOKEN or TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise SystemExit("請先在 .env 填入 DISCORD_TOKEN")
    bot.run(TOKEN)
