import aiosqlite
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "seen_jobs.db"


class Deduplicator:
    def __init__(self):
        self.db_path = DB_PATH
        self.db_path.parent.mkdir(exist_ok=True)

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS seen_jobs (
                    job_id TEXT PRIMARY KEY,
                    seen_at TEXT NOT NULL,
                    sheet_row INTEGER
                )
            """)
            await db.commit()

    async def is_seen(self, job_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,)
            ) as cursor:
                return await cursor.fetchone() is not None

    async def mark_seen(self, job_id: str, sheet_row: int = 0):
        from datetime import datetime
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO seen_jobs (job_id, seen_at, sheet_row) VALUES (?, ?, ?)",
                (job_id, datetime.now().isoformat(), sheet_row),
            )
            await db.commit()

    async def count(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM seen_jobs") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
