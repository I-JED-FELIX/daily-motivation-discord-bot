import aiosqlite


class Database:
    def __init__(self, path="data/bot.db"):
        self.path = path
        self.conn = None

    async def connect(self):
        import os
        os.makedirs("data", exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                daily_time TEXT NOT NULL DEFAULT '09:00',
                timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
                enabled INTEGER NOT NULL DEFAULT 1,
                last_posted_date TEXT
            )
        """)
        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def set_guild(self, guild_id, channel_id, daily_time, timezone, enabled=True):
        await self.conn.execute("""
            INSERT INTO guild_config
                (guild_id, channel_id, daily_time, timezone, enabled)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                channel_id=excluded.channel_id,
                daily_time=excluded.daily_time,
                timezone=excluded.timezone,
                enabled=excluded.enabled
        """, (guild_id, channel_id, daily_time, timezone, int(enabled)))
        await self.conn.commit()

    async def disable_guild(self, guild_id):
        await self.conn.execute(
            "UPDATE guild_config SET enabled=0 WHERE guild_id=?",
            (guild_id,),
        )
        await self.conn.commit()

    async def get_guild(self, guild_id):
        cur = await self.conn.execute(
            "SELECT * FROM guild_config WHERE guild_id=?",
            (guild_id,),
        )
        return await cur.fetchone()

    async def get_enabled_guilds(self):
        cur = await self.conn.execute(
            "SELECT * FROM guild_config WHERE enabled=1"
        )
        return await cur.fetchall()

    async def mark_posted(self, guild_id, date_key):
        await self.conn.execute(
            "UPDATE guild_config SET last_posted_date=? WHERE guild_id=?",
            (date_key, guild_id),
        )
        await self.conn.commit()
