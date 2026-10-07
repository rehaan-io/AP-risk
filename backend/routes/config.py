from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from database import get_db
from models.models import AppConfiguration, PolicyRule, PolicyRuleStatus, PolicyDocument

router = APIRouter(prefix="/api/config", tags=["config"])

class ConfigResponse(BaseModel):
    policy_mode: str
    po_mode: str
    setup_completed: bool

class PolicyModeUpdate(BaseModel):
    policy_mode: str

class PoModeUpdate(BaseModel):
    po_mode: str

@router.get("", response_model=ConfigResponse)
async def get_config(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppConfiguration).where(AppConfiguration.id == 1))
    config = result.scalars().first()
    if not config:
        config = AppConfiguration(id=1)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return ConfigResponse(
        policy_mode=config.policy_mode,
        po_mode=config.po_mode,
        setup_completed=config.setup_completed
    )

@router.post("/policy_mode")
async def update_policy_mode(update: PolicyModeUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppConfiguration).where(AppConfiguration.id == 1))
    config = result.scalars().first()
    if not config:
        config = AppConfiguration(id=1)
        db.add(config)
    
    config.policy_mode = update.policy_mode
    
    if update.policy_mode == 'DEFAULT_POLICY':
        # Check if default policy document exists
        doc_result = await db.execute(select(PolicyDocument).where(PolicyDocument.filename == 'SYSTEM_DEFAULT'))
        doc = doc_result.scalars().first()
        if not doc:
            doc = PolicyDocument(filename='SYSTEM_DEFAULT', extracted_text='')
            db.add(doc)
            await db.flush()
            
            defaults = [
                {
                    "rule_type": "PO_REQUIRED",
                    "conditions": {"amount": {">": 50000}},
                    "action": {"requires_po": True},
                    "scope": {"company_wide": True}
                },
                {
                    "rule_type": "TOLERANCE",
                    "conditions": {"type": "price_variance"},
                    "action": {"max_deviation_percent": 10},
                    "scope": {"company_wide": True}
                },
                {
                    "rule_type": "TOLERANCE",
                    "conditions": {"type": "quantity_variance"},
                    "action": {"max_deviation_percent": 10},
                    "scope": {"company_wide": True}
                },
                {
                    "rule_type": "TOLERANCE",
                    "conditions": {"type": "amount_variance"},
                    "action": {"max_deviation_percent": 5},
                    "scope": {"company_wide": True}
                },
                {
                    "rule_type": "INVOICE_SPLITTING",
                    "conditions": {"aggregation_window_days": 7},
                    "action": {"flag_as_split": True},
                    "scope": {"company_wide": True}
                }
            ]
            
            for i, d in enumerate(defaults):
                rule = PolicyRule(
                    document_id=doc.id,
                    rule_type=d["rule_type"],
                    scope=d["scope"],
                    conditions=d["conditions"],
                    action=d["action"],
                    priority=100 + i,
                    source_page="SYSTEM_DEFAULT",
                    requires_confirmation=False,
                    status=PolicyRuleStatus.ACTIVE
                )
                db.add(rule)
            
    await db.commit()
    return {"status": "ok"}

@router.post("/po_mode")
async def update_po_mode(update: PoModeUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppConfiguration).where(AppConfiguration.id == 1))
    config = result.scalars().first()
    if not config:
        config = AppConfiguration(id=1)
        db.add(config)
        
    config.po_mode = update.po_mode
    await db.commit()
    return {"status": "ok"}

@router.post("/complete")
async def complete_setup(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppConfiguration).where(AppConfiguration.id == 1))
    config = result.scalars().first()
    if not config:
        config = AppConfiguration(id=1)
        db.add(config)
    config.setup_completed = True
    await db.commit()
    return {"status": "ok"}
