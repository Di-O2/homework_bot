import aiosqlite

DB_NAME = "bot_database.db"

async def init_db():
    """إنشاء جداول قاعدة البيانات عند تشغيل البوت لأول مرة"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                credits INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def get_or_create_user(telegram_id: int):
    """جلب بيانات الطالب أو تسجيله برصيد تجريبي (1 نقطة)"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT credits FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
            
            # إذا كان مستخدماً جديداً، امنحه نقطة مجانية للبدء
            await db.execute("INSERT INTO users (telegram_id, credits) VALUES (?, 1)", (telegram_id,))
            await db.commit()
            return 1

async def deduct_credit(telegram_id: int) -> bool:
    """خصم نقطة واحدة بعد إتمام حل الواجب"""
    async with aiosqlite.connect(DB_NAME) as db:
        credits = await get_or_create_user(telegram_id)
        if credits > 0:
            await db.execute("UPDATE users SET credits = credits - 1 WHERE telegram_id = ?", (telegram_id,))
            await db.commit()
            return True
        return False

async def add_credits(telegram_id: int, amount: int):
    """إضافة رصيد للطالب بعد الدفع"""
    async with aiosqlite.connect(DB_NAME) as db:
        await get_or_create_user(telegram_id)
        await db.execute("UPDATE users SET credits = credits + ? WHERE telegram_id = ?", (amount, telegram_id))
        await db.commit()