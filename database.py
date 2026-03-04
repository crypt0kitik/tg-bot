import aiosqlite
from datetime import datetime

DB_PATH = "bot_data.db"


class Database:
    def __init__(self):
        self.db_path = DB_PATH

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    joined_at TEXT,
                    has_joined_channel INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0,
                    banned_at TEXT,
                    ban_reason TEXT
                )
            """)
            await db.commit()

    async def add_user(self, user_id: int, username: str, full_name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (user_id, username, full_name, joined_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, full_name, datetime.now().isoformat()))
            # Update name/username if changed
            await db.execute("""
                UPDATE users SET username=?, full_name=? WHERE user_id=?
            """, (username, full_name, user_id))
            await db.commit()

    async def mark_joined(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users SET has_joined_channel=1 WHERE user_id=?
            """, (user_id,))
            await db.commit()

    async def is_banned(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT is_banned FROM users WHERE user_id=?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return bool(row and row[0])

    async def ban_user(self, user_id: int, reason: str = ""):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users SET is_banned=1, banned_at=?, ban_reason=? WHERE user_id=?
            """, (datetime.now().isoformat(), reason, user_id))
            await db.commit()

    async def unban_user(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users SET is_banned=0, banned_at=NULL, ban_reason=NULL WHERE user_id=?
            """, (user_id,))
            await db.commit()

    async def count_users(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def count_banned(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users WHERE is_banned=1") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_all_users(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM users ORDER BY joined_at DESC
            """) as cursor:
                return [dict(row) for row in await cursor.fetchall()]

    async def get_banned_users(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM users WHERE is_banned=1 ORDER BY banned_at DESC
            """) as cursor:
                return [dict(row) for row in await cursor.fetchall()]
