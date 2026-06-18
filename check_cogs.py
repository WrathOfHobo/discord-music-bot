"""離線檢查:載入所有 cog、列出已註冊指令,不連線 Discord。"""
import asyncio

import discord

from bot import bot, INITIAL_EXTENSIONS
from music import db


async def main():
    print("opus 已載入:", discord.opus.is_loaded())
    db.init()
    for ext in INITIAL_EXTENSIONS:
        await bot.load_extension(ext)
    print("已載入 cogs:", ", ".join(bot.cogs))
    names = sorted(c.name for c in bot.tree.get_commands())
    print(f"已註冊 {len(names)} 個指令:", ", ".join(names))


asyncio.run(main())
