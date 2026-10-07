import asyncio
import asyncpg
import sys

async def create_db():
    try:
        conn = await asyncpg.connect(user="postgres", password="Rehaan@s2008", host="127.0.0.1", port=5432, database="postgres")
        # Check if exists
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname='ap_risk'")
        if not exists:
            await conn.execute("CREATE DATABASE ap_risk")
            print("Database ap_risk created.")
        else:
            print("Database ap_risk already exists.")
        await conn.close()
    except Exception as e:
        print(f"Failed to create DB: {e}")

if __name__ == "__main__":
    asyncio.run(create_db())
