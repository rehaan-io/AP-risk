from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import Optional

from database import get_db
from models.models import AuditLog

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])

@router.get("")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    target_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(AuditLog)
    
    if action:
        query = query.where(AuditLog.action == action)
    if target_id:
        query = query.where(AuditLog.target_id.ilike(f"%{target_id}%"))
        
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Paginate
    query = query.order_by(AuditLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return {
        "data": [
            {
                "id": log.id,
                "invoice_id": log.invoice_id,
                "actor": log.actor,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "action": log.action,
                "details": log.details,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }
