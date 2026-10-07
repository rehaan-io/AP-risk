from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models.models import AppConfiguration, PolicyDocument, PolicyRule, PolicyRuleReview, PurchaseOrder, PurchaseOrderItem

router = APIRouter(prefix="/api/reset", tags=["reset"])

@router.post("")
async def reset_config(db: AsyncSession = Depends(get_db)):
    # Delete all app configuration and data to start fresh
    await db.execute(AppConfiguration.__table__.delete())
    await db.execute(PolicyRuleReview.__table__.delete())
    await db.execute(PolicyRule.__table__.delete())
    await db.execute(PolicyDocument.__table__.delete())
    await db.execute(PurchaseOrderItem.__table__.delete())
    await db.execute(PurchaseOrder.__table__.delete())
    await db.commit()
    return {"status": "ok"}
