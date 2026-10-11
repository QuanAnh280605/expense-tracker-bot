import aiosqlite
from config.settings import settings

async def get_connection() -> aiosqlite.Connection:
    """Tạo kết nối async tới SQLite database."""
    conn = await aiosqlite.connect(settings.db_path)
    conn.row_factory = aiosqlite.Row
    return conn

async def init_db() -> None:
    """Khởi tạo cấu trúc các bảng trong cơ sở dữ liệu."""
    async with await get_connection() as conn:
        # 1. Bảng users
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                currency TEXT DEFAULT 'VND',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Bảng transactions
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('expense', 'income')),
                category TEXT NOT NULL,
                note TEXT,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Tạo index tăng tốc độ query thống kê
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_user_date 
            ON transactions(user_id, transaction_date)
        """)

        # 3. Bảng budgets
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                monthly_limit INTEGER NOT NULL,
                UNIQUE(user_id, category),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        await conn.commit()
