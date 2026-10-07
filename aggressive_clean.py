import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from models.models import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:Rehaan%40s2008@127.0.0.1:5432/ap_risk")
engine = create_async_engine(DATABASE_URL)

async def recreate_db():
    async with engine.begin() as conn:
        print("Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Inserting default config...")
        from sqlalchemy import text
        await conn.execute(text("""
            INSERT INTO app_config (setup_completed, policy_mode, po_mode)
            VALUES (false, 'PENDING', 'PENDING')
        """))
    print("Database fully reset and ready.")

asyncio.run(recreate_db())
