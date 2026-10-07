import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from database import engine, Base
from models.models import *

async def reset():
    print("Dropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    print("Recreating all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database is completely reset.")

if __name__ == "__main__":
    asyncio.run(reset())
