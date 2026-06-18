"""播放控制:play / nowplaying / skip(投票)/ pause / resume / stop / leave / seek / volume / loop,
以及閒置自動離開。"""
import discord
from discord import app_commands
from discord.ext import commands, tasks

from .. import sources
from ..player import get_player, Track, LoopMode
from ..format import fmt_duration, progress_bar, parse_seek


async def connect(interaction: discord.Interaction):
    """確保 bot 在使用者的語音頻道,回傳 player;使用者不在語音則回 None。"""
    if not interaction.user.voice:
        return None
    player = get_player(interaction.client, interaction.guild)
    ch = interaction.user.voice.channel
    if player.voice is None or not player.voice.is_connected():
        player.voice = await ch.connect()
    elif player.voice.channel != ch:
        await player.voice.move_to(ch)
    return player


class Playback(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.idle_check.start()

    async def cog_unload(self):
        self.idle_check.cancel()

    @app_commands.command(description="播放歌曲(YouTube 網址或關鍵字)")
    @app_commands.describe(query="YouTube 網址或搜尋關鍵字")
    async def play(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice:
            await interaction.response.send_message("你要先加入語音頻道", ephemeral=True)
            return
        await interaction.response.defer()
        player = await connect(interaction)

        # 整張 YouTube 播放清單:flat 展開,全部排入(不設上限)
        if sources.is_playlist_url(query):
            try:
                title, entries = await sources.resolve_playlist(query)
            except Exception as e:
                await interaction.followup.send(f"清單解析失敗:`{e}`")
                return
            added = 0
            for ent in entries:
                t = Track.from_search_entry(ent, interaction.user)
                if t.webpage_url:
                    player.queue.append(t)
                    added += 1
            if not added:
                await interaction.followup.send("這張清單沒有可播放的項目")
                return
            await player.ensure_playing()
            await interaction.followup.send(f"📋 已從清單 **{title}** 加入 **{added}** 首")
            return

        # 單曲(網址或關鍵字)
        try:
            info = await sources.resolve(query)
        except Exception as e:
            await interaction.followup.send(f"解析失敗:`{e}`")
            return
        if not info:
            await interaction.followup.send("找不到結果")
            return
        track = Track.from_info(info, interaction.user)
        was_active = bool(player.current) or player.voice.is_playing() or player.voice.is_paused()
        player.queue.append(track)
        await player.ensure_playing()
        await interaction.followup.send(
            (f"➕ 已加入佇列:**{track.title}**" if was_active else f"▶️ 播放:**{track.title}**")
        )

    @app_commands.command(description="顯示目前播放中的歌曲")
    async def nowplaying(self, interaction: discord.Interaction):
        player = get_player(self.bot, interaction.guild)
        if not player.current:
            await interaction.response.send_message("目前沒有在播放", ephemeral=True)
            return
        t = player.current
        pos = player.position
        e = discord.Embed(title="正在播放", description=f"**{t.title}**", color=0x1DB954)
        e.add_field(
            name="進度",
            value=f"{progress_bar(pos, t.duration)}\n`{fmt_duration(pos)} / {fmt_duration(t.duration)}`",
            inline=False,
        )
        e.add_field(name="點歌", value=t.requester_name, inline=True)
        e.add_field(name="來源", value=t.source, inline=True)
        if player.voice and player.voice.is_paused():
            e.add_field(name="狀態", value="⏸️ 暫停中", inline=True)
        if t.thumbnail:
            e.set_thumbnail(url=t.thumbnail)
        await interaction.response.send_message(embed=e)

    @app_commands.command(description="投票跳過目前歌曲(房主/點歌人可直接跳)")
    async def skip(self, interaction: discord.Interaction):
        player = get_player(self.bot, interaction.guild)
        if not player.current or not player.voice:
            await interaction.response.send_message("現在沒有在播放", ephemeral=True)
            return
        member = interaction.user
        if member.id == player.current.requester_id or member.guild_permissions.manage_guild:
            await player.skip()
            await interaction.response.send_message("⏭️ 已跳過")
            return
        humans = [m for m in player.voice.channel.members if not m.bot]
        needed = len(humans) // 2 + 1
        player.votes.add(member.id)
        if len(player.votes) >= needed:
            await player.skip()
            await interaction.response.send_message("⏭️ 投票通過,已跳過")
        else:
            await interaction.response.send_message(f"🗳️ 跳過投票:{len(player.votes)}/{needed}")

    @app_commands.command(description="暫停")
    async def pause(self, interaction: discord.Interaction):
        player = get_player(self.bot, interaction.guild)
        await interaction.response.send_message("⏸️ 已暫停" if player.pause() else "現在沒有在播放")

    @app_commands.command(description="繼續播放")
    async def resume(self, interaction: discord.Interaction):
        player = get_player(self.bot, interaction.guild)
        await interaction.response.send_message("▶️ 繼續播放" if player.resume() else "沒有暫停中的歌曲")

    @app_commands.command(description="停止並清空佇列")
    async def stop(self, interaction: discord.Interaction):
        player = get_player(self.bot, interaction.guild)
        await player.stop()
        await interaction.response.send_message("⏹️ 已停止並清空佇列")

    @app_commands.command(description="讓機器人離開語音頻道")
    async def leave(self, interaction: discord.Interaction):
        player = get_player(self.bot, interaction.guild)
        await player.stop()
        if player.voice:
            await player.voice.disconnect()
            player.voice = None
        await interaction.response.send_message("👋 掰掰")

    @app_commands.command(description="跳轉:絕對 1:23 或相對 +30 / -15")
    @app_commands.describe(position="例如 90、1:23、1:02:03、1m30s,或 +30 / -15")
    async def seek(self, interaction: discord.Interaction, position: str):
        player = get_player(self.bot, interaction.guild)
        if not player.current:
            await interaction.response.send_message("現在沒有在播放", ephemeral=True)
            return
        if not player.current.duration:
            await interaction.response.send_message("這是直播或長度未知,無法跳轉", ephemeral=True)
            return
        parsed = parse_seek(position)
        if not parsed:
            await interaction.response.send_message("時間格式看不懂,例:90 / 1:23 / +30 / -15", ephemeral=True)
            return
        mode, val = parsed
        target = val if mode == "abs" else player.position + val
        target = max(0, min(target, player.current.duration - 1))
        await interaction.response.defer()
        await player.seek(target)
        await interaction.followup.send(f"⏩ 跳到 `{fmt_duration(target)}`")

    @app_commands.command(description="設定音量(0-200,100 為原音量)")
    @app_commands.describe(percent="音量百分比")
    async def volume(self, interaction: discord.Interaction, percent: app_commands.Range[int, 0, 200]):
        player = get_player(self.bot, interaction.guild)
        player.set_volume(percent / 100)
        await interaction.response.send_message(f"🔊 音量:{percent}%")

    @app_commands.command(description="循環模式")
    @app_commands.choices(mode=[
        app_commands.Choice(name="關閉", value="off"),
        app_commands.Choice(name="單曲循環", value="track"),
        app_commands.Choice(name="整列循環", value="queue"),
    ])
    async def loop(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        player = get_player(self.bot, interaction.guild)
        player.loop_mode = {"off": LoopMode.OFF, "track": LoopMode.TRACK, "queue": LoopMode.QUEUE}[mode.value]
        await interaction.response.send_message(f"🔁 循環:{mode.name}")

    @tasks.loop(minutes=2)
    async def idle_check(self):
        for player in list(self.bot.players.values()):
            vc = player.voice
            if not vc or not vc.is_connected():
                continue
            humans = [m for m in vc.channel.members if not m.bot]
            idle = not vc.is_playing() and not vc.is_paused() and not player.queue
            player.idle_ticks = player.idle_ticks + 1 if (not humans or idle) else 0
            if player.idle_ticks >= 2:  # 約 4 分鐘
                await player.stop()
                await vc.disconnect()
                player.voice = None
                player.idle_ticks = 0

    @idle_check.before_loop
    async def _before_idle(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Playback(bot))
