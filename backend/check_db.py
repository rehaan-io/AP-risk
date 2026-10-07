import asyncio
from database import engine
from sqlalchemy import text

async def check_db():
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT COUNT(*) FROM invoices"))
        count = res.scalar()
        print(f"Total invoices in DB: {count}")

        res = await conn.execute(text("SELECT COUNT(*) FROM invoice_items"))
        count = res.scalar()
        print(f"Total invoice_items in DB: {count}")

if __name__ == "__main__":
    asyncio.run(check_db())
