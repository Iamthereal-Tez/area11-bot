"""
Database abstraction supporting SQLite (local) and Postgres (DATABASE_URL env).
Provides simple tables for levels/XP and warns, with basic operations.

Usage:
- Create Database() and call await connect()
- await create_tables()
- await add_xp(user_id, guild_id, amount)
- await get_user(user_id, guild_id)
- await get_leaderboard(guild_id, limit)
- await set_xp(user_id, guild_id, xp)
- await reset_user(user_id, guild_id)
- await add_warn(user_id, guild_id)
- await get_warns(user_id, guild_id)
- await reset_warns(user_id, guild_id)
- await close()
"""

import os
import aiosqlite
import asyncpg
import math

class Database:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self._pg_pool = None
        self._sqlite_conn = None
        self._using_pg = False

    async def connect(self):
        if self.database_url and self.database_url.startswith("postgres"):
            # Using Postgres
            self._pg_pool = await asyncpg.create_pool(dsn=self.database_url, min_size=1, max_size=5)
            self._using_pg = True
            print("Using PostgreSQL database")
        else:
            # Fallback to SQLite file
            self._sqlite_conn = await aiosqlite.connect("levels.db")
            await self._sqlite_conn.execute("PRAGMA journal_mode=WAL;")
            await self._sqlite_conn.commit()
            self._using_pg = False
            print("Using SQLite database")

    async def create_tables(self):
        if self._using_pg:
            async with self._pg_pool.acquire() as conn:
                # XP table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS xp (
                        guild_id BIGINT,
                        user_id BIGINT,
                        xp BIGINT DEFAULT 0,
                        PRIMARY KEY (guild_id, user_id)
                    );
                """)
                # Warn table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS warns (
                        guild_id BIGINT,
                        user_id BIGINT,
                        warns INTEGER DEFAULT 0,
                        PRIMARY KEY (guild_id, user_id)
                    );
                """)
        else:
            # SQLite
            await self._sqlite_conn.execute("""
                CREATE TABLE IF NOT EXISTS xp (
                    guild_id INTEGER,
                    user_id INTEGER,
                    xp INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                );
            """)
            await self._sqlite_conn.execute("""
                CREATE TABLE IF NOT EXISTS warns (
                    guild_id INTEGER,
                    user_id INTEGER,
                    warns INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                );
            """)
            await self._sqlite_conn.commit()

    # ---------------- XP helpers ----------------
    async def add_xp(self, user_id: int, guild_id: int, amount: int = 1):
        if self._using_pg:
            async with self._pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO xp (guild_id, user_id, xp) VALUES ($1, $2, $3)
                    ON CONFLICT (guild_id, user_id) DO UPDATE SET xp = xp + $3;
                """, guild_id, user_id, amount)
        else:
            async with self._sqlite_conn.execute("SELECT xp FROM xp WHERE guild_id=? AND user_id=?", (guild_id, user_id)) as cur:
                row = await cur.fetchone()
            if row is None:
                await self._sqlite_conn.execute("INSERT INTO xp (guild_id, user_id, xp) VALUES (?, ?, ?)", (guild_id, user_id, amount))
            else:
                new_xp = row[0] + amount
                await self._sqlite_conn.execute("UPDATE xp SET xp=? WHERE guild_id=? AND user_id=?", (new_xp, guild_id, user_id))
            await self._sqlite_conn.commit()

    async def get_user(self, user_id: int, guild_id: int):
        if self._using_pg:
            async with self._pg_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT xp FROM xp WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
                return row["xp"] if row else 0
        else:
            async with self._sqlite_conn.execute("SELECT xp FROM xp WHERE guild_id=? AND user_id=?", (guild_id, user_id)) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

    async def set_xp(self, user_id: int, guild_id: int, xp: int):
        if self._using_pg:
            async with self._pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO xp (guild_id, user_id, xp) VALUES ($1, $2, $3)
                    ON CONFLICT (guild_id, user_id) DO UPDATE SET xp=$3;
                """, guild_id, user_id, xp)
        else:
            await self._sqlite_conn.execute("INSERT OR REPLACE INTO xp (guild_id, user_id, xp) VALUES (?, ?, ?)", (guild_id, user_id, xp))
            await self._sqlite_conn.commit()

    async def reset_user(self, user_id: int, guild_id: int):
        if self._using_pg:
            async with self._pg_pool.acquire() as conn:
                await conn.execute("DELETE FROM xp WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
        else:
            await self._sqlite_conn.execute("DELETE FROM xp WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            await self._sqlite_conn.commit()

    async def get_leaderboard(self, guild_id: int, limit: int = 10):
        if self._using_pg:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch("SELECT user_id, xp FROM xp WHERE guild_id=$1 ORDER BY xp DESC LIMIT $2", guild_id, limit)
                return [(r["user_id"], r["xp"]) for r in rows]
        else:
            async with self._sqlite_conn.execute("SELECT user_id, xp FROM xp WHERE guild_id=? ORDER BY xp DESC LIMIT ?", (guild_id, limit)) as cur:
                rows = await cur.fetchall()
                return [(r[0], r[1]) for r in rows]

    # ---------------- WARN helpers ----------------
    async def add_warn(self, user_id: int, guild_id: int):
        """Add a warn to a user and return total warns."""
        if self._using_pg:
            async with self._pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO warns (guild_id, user_id, warns) VALUES ($1, $2, 1)
                    ON CONFLICT (guild_id, user_id) DO UPDATE SET warns = warns + 1;
                """, guild_id, user_id)
                row = await conn.fetchrow("SELECT warns FROM warns WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
                return row["warns"]
        else:
            async with self._sqlite_conn.execute("SELECT warns FROM warns WHERE guild_id=? AND user_id=?", (guild_id, user_id)) as cur:
                row = await cur.fetchone()
            if row is None:
                await self._sqlite_conn.execute("INSERT INTO warns (guild_id, user_id, warns) VALUES (?, ?, 1)", (guild_id, user_id))
                await self._sqlite_conn.commit()
                return 1
            else:
                new_warns = row[0] + 1
                await self._sqlite_conn.execute("UPDATE warns SET warns=? WHERE guild_id=? AND user_id=?", (new_warns, guild_id, user_id))
                await self._sqlite_conn.commit()
                return new_warns

    async def get_warns(self, user_id: int, guild_id: int):
        if self._using_pg:
            async with self._pg_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT warns FROM warns WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
                return row["warns"] if row else 0
        else:
            async with self._sqlite_conn.execute("SELECT warns FROM warns WHERE guild_id=? AND user_id=?", (guild_id, user_id)) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

    async def reset_warns(self, user_id: int, guild_id: int):
        if self._using_pg:
            async with self._pg_pool.acquire() as conn:
                await conn.execute("DELETE FROM warns WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
        else:
            await self._sqlite_conn.execute("DELETE FROM warns WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            await self._sqlite_conn.commit()

    # ---------------- Misc ----------------
    @staticmethod
    def xp_to_level(xp: int) -> int:
        # Updated to use exponential formula: level = floor(0.1 * sqrt(xp)) + 1
        return math.floor(0.1 * math.sqrt(xp)) + 1 if xp > 0 else 1

    async def close(self):
        if self._using_pg and self._pg_pool:
            await self._pg_pool.close()
        if self._sqlite_conn:
            await self._sqlite_conn.close()
