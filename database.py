import aiosqlite
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Optional, Tuple, Any

class Database:
    def __init__(self, db_name: str = "data/personal_expenses.db"):
        self.db_name = db_name
        self.timezone = pytz.timezone('Asia/Tashkent')

    async def create_tables(self):
        async with aiosqlite.connect(self.db_name) as db:
            # Create users table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create categories table with user_id
            await db.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    UNIQUE(user_id, name),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # Create expenses table with user_id
            await db.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    category_id INTEGER,
                    description TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (category_id) REFERENCES categories (id)
                )
            ''')
            await db.commit()

    async def get_or_create_user(self, telegram_id: int) -> int:
        """Get or create user and return user_id"""
        async with aiosqlite.connect(self.db_name) as db:
            # Try to get existing user
            cursor = await db.execute(
                'SELECT id FROM users WHERE telegram_id = ?',
                (telegram_id,)
            )
            user = await cursor.fetchone()

            if user:
                return user[0]

            # Create new user
            await db.execute(
                'INSERT INTO users (telegram_id) VALUES (?)',
                (telegram_id,)
            )
            await db.commit()

            # Get the new user's id
            cursor = await db.execute(
                'SELECT id FROM users WHERE telegram_id = ?',
                (telegram_id,)
            )
            user = await cursor.fetchone()

            # Create default categories for the new user
            default_categories = [
                "🏠 Uy-joy", "🍽️ Oziq-ovqat", "🚗 Transport",
                "👕 Kiyim-kechak", "💊 Sog'liq", "📚 Ta'lim",
                "🎮 Ko'ngil ochar", "🛍️ Boshqa"
            ]
            for category in default_categories:
                await db.execute(
                    'INSERT OR IGNORE INTO categories (user_id, name) VALUES (?, ?)',
                    (user[0], category)
                )
            await db.commit()

            return user[0]

    async def initialize_categories(self, user_id: int):
        """Initialize default categories for new user"""
        default_categories = [
            "🏠 Uy-joy", "🍽️ Ovqat", "🚗 Transport", 
            "🏥 Sog'liq", "👕 Kiyim", "📱 Aloqa",
            "🎓 Ta'lim", "🎮 Ko'ngil ochar", "💝 Sovg'alar",
            "💰 Boshqa"
        ]
        
        async with aiosqlite.connect(self.db_name) as db:
            await db.executemany(
                "INSERT OR IGNORE INTO categories (user_id, name) VALUES (?, ?)",
                [(user_id, category) for category in default_categories]
            )
            await db.commit()

    async def add_expense(self, user_id: int, amount: int, category_id: int, description: str = None) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            current_time = datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S')
            await db.execute(
                "INSERT INTO expenses (user_id, amount, category_id, description, date) VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category_id, description, current_time)
            )
            await db.commit()
            return True

    async def get_categories(self, user_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM categories WHERE user_id = ? ORDER BY name",
                (user_id,)
            ) as cursor:
                return [dict(row) for row in await cursor.fetchall()]

    async def get_category_by_id(self, category_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM categories WHERE id = ? AND user_id = ?",
                (category_id, user_id)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_expenses(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT e.*, c.name as category_name 
                FROM expenses e 
                LEFT JOIN categories c ON e.category_id = c.id 
                WHERE e.user_id = ?
                ORDER BY e.date DESC 
                LIMIT ?
            """
            async with db.execute(query, (user_id, limit)) as cursor:
                return [dict(row) for row in await cursor.fetchall()]

    async def get_monthly_summary(self, user_id: int, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Get monthly expenses summary for user"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT 
                    c.name as category_name,
                    SUM(e.amount) as total_amount
                FROM expenses e 
                LEFT JOIN categories c ON e.category_id = c.id 
                WHERE e.user_id = ?
                AND date(e.date) >= date(?)
                AND date(e.date) <= date(?)
                GROUP BY c.name
                ORDER BY total_amount DESC
            """
            params = [user_id]
            
            if start_date and end_date:
                params.extend([start_date, end_date])
            else:
                # Default to current month if no dates provided
                now = datetime.now(self.timezone)
                start_of_month = now.replace(day=1).strftime('%Y-%m-%d')
                end_of_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                params.extend([start_of_month, end_of_month.strftime('%Y-%m-%d')])
            
            async with db.execute(query, params) as cursor:
                return [dict(row) for row in await cursor.fetchall()]

    async def get_daily_summary(self, user_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT 
                    date(e.date) as expense_date,
                    SUM(e.amount) as total_amount
                FROM expenses e 
                WHERE e.user_id = ? AND e.date >= date('now', '-7 days')
                GROUP BY date(e.date)
                ORDER BY expense_date DESC
            """
            async with db.execute(query, (user_id,)) as cursor:
                return [dict(row) for row in await cursor.fetchall()]

    async def get_expenses_by_date_range(self, user_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get expenses within date range"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT 
                    e.date,
                    e.amount,
                    c.name as category_name,
                    e.description
                FROM expenses e 
                LEFT JOIN categories c ON e.category_id = c.id 
                WHERE e.user_id = ?
                AND date(e.date) >= date(?) 
                AND date(e.date) <= date(?)
                ORDER BY e.date ASC, e.id ASC
            """
            async with db.execute(query, (user_id, start_date, end_date)) as cursor:
                return [dict(row) for row in await cursor.fetchall()]

    async def get_category_summary_by_date_range(self, user_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT 
                    c.name as category_name,
                    COUNT(*) as count,
                    SUM(e.amount) as total_amount
                FROM expenses e 
                LEFT JOIN categories c ON e.category_id = c.id 
                WHERE e.user_id = ?
                AND date(e.date) >= date(?)
                AND date(e.date) <= date(?)
                GROUP BY c.id, c.name
                ORDER BY total_amount DESC
            """
            async with db.execute(query, (user_id, start_date, end_date)) as cursor:
                return [dict(row) for row in await cursor.fetchall()]

    async def get_daily_summary_by_date_range(self, user_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT 
                    date(e.date) as expense_date,
                    SUM(e.amount) as total_amount,
                    COUNT(*) as count
                FROM expenses e 
                WHERE e.user_id = ?
                AND date(e.date) >= date(?)
                AND date(e.date) <= date(?)
                GROUP BY date(e.date)
                ORDER BY expense_date
            """
            async with db.execute(query, (user_id, start_date, end_date)) as cursor:
                return [dict(row) for row in await cursor.fetchall()]

    async def reset_tables(self):
        """Drop and recreate all tables"""
        async with aiosqlite.connect(self.db_name) as db:
            # Drop existing tables in reverse order of dependencies
            await db.execute('DROP TABLE IF EXISTS expenses')
            await db.execute('DROP TABLE IF EXISTS categories')
            await db.execute('DROP TABLE IF EXISTS users')
            await db.commit()
            
            # Recreate tables
            await self.create_tables()
