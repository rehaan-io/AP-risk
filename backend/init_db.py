import asyncio
from database import engine, Base
# Import all models to ensure they are registered with Base
from models.models import Invoice, InvoiceItem, RiskResult, AuditLog

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created.")

if __name__ == "__main__":
    asyncio.run(init_db())
