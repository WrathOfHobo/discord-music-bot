"""Discord 互動元件:搜尋選單、佇列分頁。"""
import math

import discord

from .format import fmt_duration


class _SearchSelect(discord.ui.Select):
    def __init__(self, entries, on_pick):
        self.entries = entries
        self.on_pick = on_pick
        options = []
        for i, e in enumerate(entries):
            title = (e.get("title") or "未知")[:90]
            dur = e.get("duration")
            options.append(
                discord.SelectOption(
                    label=f"{i + 1}. {title}"[:100],
                    description=(fmt_duration(dur) if dur else "")[:100],
                    value=str(i),
                )
            )
        super().__init__(placeholder="選擇要播放的曲目…", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        await self.on_pick(interaction, self.entries[int(self.values[0])])


class SearchView(discord.ui.View):
    def __init__(self, entries, on_pick, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.add_item(_SearchSelect(entries, on_pick))


class QueueView(discord.ui.View):
    """佇列分頁。每頁 10 首,用上下頁按鈕翻。"""

    def __init__(self, player, per_page: int = 10, timeout: float = 120, page: int = 0):
        super().__init__(timeout=timeout)
        self.player = player
        self.per_page = per_page
        self.page = page

    def total_pages(self) -> int:
        return max(1, math.ceil(len(self.player.queue) / self.per_page))

    def embed(self) -> discord.Embed:
        self.page = max(0, min(self.page, self.total_pages() - 1))
        p = self.player
        e = discord.Embed(title="🎵 播放佇列", color=0x5865F2)
        if p.current:
            e.add_field(
                name="正在播放",
                value=f"**{p.current.title}** ({fmt_duration(p.current.duration)})",
                inline=False,
            )
        start = self.page * self.per_page
        chunk = p.queue[start:start + self.per_page]
        if chunk:
            lines = [
                f"`{start + i + 1}.` {t.title} ({fmt_duration(t.duration)}) — {t.requester_name}"
                for i, t in enumerate(chunk)
            ]
            e.description = "\n".join(lines)
        else:
            e.description = "佇列是空的"
        total_sec = sum(t.duration for t in p.queue)
        e.set_footer(
            text=f"第 {self.page + 1}/{self.total_pages()} 頁 · 共 {len(p.queue)} 首 · "
                 f"總長 {fmt_duration(total_sec)} · 循環:{p.loop_mode.name} · 電台:{'開' if p.autoplay else '關'}"
        )
        return e

    @discord.ui.button(label="◀ 上一頁", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page - 1) % self.total_pages()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="下一頁 ▶", style=discord.ButtonStyle.secondary)
    async def nxt(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page + 1) % self.total_pages()
        await interaction.response.edit_message(embed=self.embed(), view=self)
