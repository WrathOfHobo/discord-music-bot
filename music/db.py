"""SQLite:儲存具名歌單(每個伺服器)。"""
import json
import os
import sqlite3

_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.db")


def _conn():
    c = sqlite3.connect(_DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS playlists(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                tracks TEXT NOT NULL,
                UNIQUE(guild_id, name)
            )"""
        )


def save_playlist(guild_id, owner_id, name, tracks: list[dict]):
    data = json.dumps(tracks, ensure_ascii=False)
    with _conn() as c:
        c.execute(
            "INSERT INTO playlists(guild_id, owner_id, name, tracks) VALUES(?,?,?,?) "
            "ON CONFLICT(guild_id, name) DO UPDATE SET tracks=excluded.tracks, owner_id=excluded.owner_id",
            (guild_id, owner_id, name, data),
        )


def list_playlists(guild_id) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT name, owner_id, tracks FROM playlists WHERE guild_id=? ORDER BY name", (guild_id,)
        ).fetchall()
    out = []
    for r in rows:
        out.append({"name": r["name"], "owner_id": r["owner_id"], "count": len(json.loads(r["tracks"]))})
    return out


def get_playlist(guild_id, name) -> list[dict] | None:
    with _conn() as c:
        row = c.execute(
            "SELECT tracks FROM playlists WHERE guild_id=? AND name=?", (guild_id, name)
        ).fetchone()
    return json.loads(row["tracks"]) if row else None


def delete_playlist(guild_id, name) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM playlists WHERE guild_id=? AND name=?", (guild_id, name))
        return cur.rowcount > 0
