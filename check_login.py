"""快速診斷:只登入 Discord,印出結果就登出。用來確認 token 與連線是否正常。"""
import os
import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"LOGIN_OK 登入成功: {client.user} (id={client.user.id})")
    print(f"已加入伺服器數: {len(client.guilds)}")
    for g in client.guilds:
        print(f"  - {g.name}")
    await client.close()


if __name__ == "__main__":
    if not TOKEN or TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise SystemExit("TOKEN 未填")
    try:
        client.run(TOKEN)
    except discord.LoginFailure:
        print("LOGIN_FAIL: token 無效(可能複製錯或被 Reset 過)")
