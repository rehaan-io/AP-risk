from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes import invoices, purchase_orders, policies, config, reset

app = FastAPI(title="AP Risk Intelligence System")

import os
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "AP Risk Intelligence Backend is running"}

app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
app.include_router(purchase_orders.router)
app.include_router(policies.router)
app.include_router(config.router)
app.include_router(reset.router)

from routes import audit_logs
app.include_router(audit_logs.router)

# Map the dashboard stats from invoices router to the requested path
@app.get("/api/dashboard/stats")
async def get_dashboard_stats(db=__import__("fastapi").Depends(__import__("database").get_db)):
    return await invoices.get_stats(db)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
