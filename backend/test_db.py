import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from models.models import Invoice

async def test_db():
    engine = create_async_engine("postgresql+asyncpg://postgres:Rehaan%40s2008@127.0.0.1:5432/ap_risk", echo=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # Check current count
        res = await session.execute(text("SELECT COUNT(*) FROM invoices"))
        print(f"Count before: {res.scalar()}")
        
        # Insert one
        inv = Invoice(invoice_number="TEST-001", vendor_name="Test Vendor")
        session.add(inv)
        await session.commit()
        
        # Check count again
        res = await session.execute(text("SELECT COUNT(*) FROM invoices"))
        print(f"Count after: {res.scalar()}")

if __name__ == "__main__":
    asyncio.run(test_db())
