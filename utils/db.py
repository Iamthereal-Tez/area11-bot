import aiosqlite
import os

DB_PATH = os.getenv("DB_PATH", "levels.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await db.commit()

async def get_user(guild_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT xp, level FROM users WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        row = await cur.fetchone()
        return row

async def set_user(guild_id: int, user_id: int, xp: int, level: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (guild_id, user_id, xp, level)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET xp=excluded.xp, level=excluded.level
        """, (guild_id, user_id, xp, level))
        await db.commit()

async def add_xp(guild_id: int, user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT xp, level FROM users WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        row = await cur.fetchone()
        if row:
            xp, level = row
            xp += amount
        else:
            xp = amount
            level = 0
        await db.execute("""
            INSERT INTO users (guild_id, user_id, xp, level)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET xp=excluded.xp
        """, (guild_id, user_id, xp, level))
        await db.commit()
        return xp, level

async def set_level(guild_id: int, user_id: int, new_level: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET level = ? WHERE guild_id = ? AND user_id = ?", (new_level, guild_id, user_id))
        await db.commit()

async def top_users(guild_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, xp, level FROM users WHERE guild_id = ? ORDER BY xp DESC LIMIT ?", (guild_id, limit))
        rows = await cur.fetchall()
        return rows
