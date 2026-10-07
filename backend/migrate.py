import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:Rehaan%40s2008@127.0.0.1:5432/ap_risk")
engine = create_async_engine(DATABASE_URL, echo=True)

async def migrate():
    async with engine.begin() as conn:
        # Commit manually for ENUM alter outside transaction block
        try:
            await conn.execute(text("COMMIT"))
            await conn.execute(text("ALTER TYPE invoicestatusenum ADD VALUE IF NOT EXISTS 'INFORMATION_REQUESTED'"))
        except Exception as e:
            print("Enum alter error:", e)
        
        try:
            await conn.execute(text("ALTER TABLE invoices ADD COLUMN ai_explanation TEXT"))
        except Exception as e:
            print("Column alter error:", e)
            
        try:
            await conn.execute(text("ALTER TABLE audit_logs ADD COLUMN actor VARCHAR DEFAULT 'System'"))
            await conn.execute(text("ALTER TABLE audit_logs ADD COLUMN target_type VARCHAR"))
            await conn.execute(text("ALTER TABLE audit_logs ADD COLUMN target_id VARCHAR"))
        except Exception as e:
            print("Audit log alter error:", e)

asyncio.run(migrate())
