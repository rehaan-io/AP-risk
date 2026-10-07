import uuid
import zipfile
import io
import asyncio
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import Dict, Any

from database import get_db
from models.models import Invoice, InvoiceItem, RiskResult, AuditLog, InvoiceStatusEnum, RiskLevelEnum
from schemas.schemas import InvoiceSchema, DashboardStats
from services.azure_document_intelligence import analyze_invoice_bytes
from services.risk_engine import evaluate_invoice
from sqlalchemy.orm import selectinload

router = APIRouter()

# In-memory store for task progress queues
progress_queues: Dict[str, asyncio.Queue] = {}

from database import AsyncSessionLocal

async def process_zip_task(task_id: str, zip_bytes: bytes):
    queue = progress_queues.get(task_id)
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            valid_exts = ('.pdf', '.jpg', '.jpeg', '.png')
            files = [f for f in z.namelist() if f.lower().endswith(valid_exts) and not f.startswith('__MACOSX/')]
            
            total = len(files)
            if queue:
                await queue.put({"type": "start", "total": total})

            processed = 0
            stats = {"AUTO_PASSED": 0, "HUMAN_REVIEW": 0, "HIGH_RISK": 0, "FAILED": 0}

            semaphore = asyncio.Semaphore(10)
            
            async def process_file(filename):
                nonlocal processed
                file_data = z.read(filename)
                try:
                    async with semaphore:
                        extracted = await analyze_invoice_bytes(file_data)
                    
                    async with AsyncSessionLocal() as session:
                        import re
                        risks, status, overall_risk, risk_score, confidence = await evaluate_invoice(session, extracted)
                        
                        import datetime
                        def parse_date(date_val):
                            if not date_val: return None
                            if isinstance(date_val, str):
                                try:
                                    return datetime.datetime.fromisoformat(date_val.split('T')[0])
                                except ValueError:
                                    return None
                            if type(date_val) is datetime.date:
                                return datetime.datetime.combine(date_val, datetime.datetime.min.time())
                            return date_val

                        v_raw = extracted.get("vendor_name")
                        n_vendor = re.sub(r'[^a-z0-9]', '', str(v_raw).lower().strip()) if v_raw else None
                        
                        i_raw = extracted.get("invoice_number")
                        n_invoice = re.sub(r'[^a-z0-9]', '', str(i_raw).lower().strip()) if i_raw else None

                        new_invoice = Invoice(
                            invoice_number=i_raw,
                            normalized_invoice_number=n_invoice,
                            vendor_name=v_raw,
                            normalized_vendor=n_vendor,
                            vendor_address=extracted.get("vendor_address"),
                            invoice_date=parse_date(extracted.get("invoice_date")),
                            due_date=parse_date(extracted.get("due_date")),
                            po_number=extracted.get("po_number"),
                            subtotal=extracted.get("subtotal"),
                            tax=extracted.get("tax"),
                            total_amount=extracted.get("total_amount"),
                            currency=extracted.get("currency"),
                            payment_terms=extracted.get("payment_terms"),
                            status=status,
                            risk_level=overall_risk,
                            risk_score=risk_score,
                            confidence=confidence
                        )
                        session.add(new_invoice)
                        await session.flush()
                        
                        for item in extracted.get("items", []):
                            d_raw = item.get("description")
                            n_desc = re.sub(r'[^a-z0-9]', '', str(d_raw).lower().strip()) if d_raw else None
                            session.add(InvoiceItem(
                                invoice_id=new_invoice.id,
                                description=d_raw,
                                normalized_description=n_desc,
                                quantity=item.get("quantity"),
                                unit_price=item.get("unit_price"),
                                amount=item.get("amount")
                            ))
                        
                        for r in risks:
                            session.add(RiskResult(
                                invoice_id=new_invoice.id,
                                risk_type=r["risk_type"],
                                risk_level=r["risk_level"],
                                reason=r["reason"],
                                confidence=r["confidence"],
                                score_contribution=r["score_contribution"],
                                evidence=r["evidence"]
                            ))
                            
                        session.add(AuditLog(
                            invoice_id=new_invoice.id,
                            action="DOCUMENT_EXTRACTED",
                            details="Invoice successfully extracted from PDF/image."
                        ))
                        if len(risks) > 0:
                            session.add(AuditLog(
                                invoice_id=new_invoice.id,
                                action="RISK_DETECTED",
                                details=f"{len(risks)} risk(s) detected. Score: {risk_score:.2f}."
                            ))
                        
                        await session.commit()

                    stats[status.name] += 1
                    if overall_risk == RiskLevelEnum.HIGH:
                        stats["HIGH_RISK"] += 1

                except Exception as e:
                    stats["FAILED"] += 1
                    print(f"Error processing {filename}: {e}")
                    with open("error_log.txt", "a") as f:
                        import traceback
                        f.write(f"File {filename}: {traceback.format_exc()}\n")
                
                processed += 1
                if queue:
                    await queue.put({
                        "type": "progress", 
                        "processed": processed, 
                        "total": total, 
                        "current": filename
                    })

            # Process all in parallel with semaphore limit
            tasks = [process_file(f) for f in files]
            await asyncio.gather(*tasks)

            if queue:
                await queue.put({
                    "type": "complete",
                    "total": total,
                    "stats": stats
                })

    except Exception as e:
        import traceback
        with open("fatal_error.txt", "a") as f:
            f.write("INVOICE TASK FATAL:\n" + traceback.format_exc() + "\n")
        if queue:
            await queue.put({"type": "error", "message": str(e)})
    finally:
        if queue:
            await queue.put(None) # EOF marker

@router.post("/upload-zip")
async def upload_zip(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Must be a ZIP file")
    
    zip_bytes = await file.read()
    task_id = str(uuid.uuid4())
    progress_queues[task_id] = asyncio.Queue()
    
    # Run the processing in the background
    background_tasks.add_task(process_zip_task, task_id, zip_bytes)
    
    return {"task_id": task_id}

@router.get("/progress/{task_id}")
async def get_progress(task_id: str):
    queue = progress_queues.get(task_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        try:
            while True:
                data = await queue.get()
                if data is None:
                    break
                import json
                yield f"data: {json.dumps(data)}\n\n"
        finally:
            if task_id in progress_queues:
                del progress_queues[task_id]

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("", response_model=list[InvoiceSchema])
async def get_invoices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).options(selectinload(Invoice.items), selectinload(Invoice.risks), selectinload(Invoice.logs)))
    return result.scalars().all()

@router.get("/exceptions", response_model=list[InvoiceSchema])
async def get_exceptions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.status == InvoiceStatusEnum.HUMAN_REVIEW).options(selectinload(Invoice.items), selectinload(Invoice.risks)))
    return result.scalars().all()

@router.get("/{id}", response_model=InvoiceSchema)
async def get_invoice(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == id).options(selectinload(Invoice.items), selectinload(Invoice.risks), selectinload(Invoice.logs)))
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@router.post("/{id}/approve")
async def approve_invoice(id: int, db: AsyncSession = Depends(get_db)):
    invoice = await get_invoice(id, db)
    invoice.status = InvoiceStatusEnum.APPROVED
    db.add(AuditLog(
        invoice_id=id, actor="System User", target_type="INVOICE", target_id=invoice.invoice_number,
        action="HUMAN_APPROVED", details="Manually approved by user."
    ))
    await db.commit()
    return {"message": "Approved"}

@router.post("/{id}/reject")
async def reject_invoice(id: int, db: AsyncSession = Depends(get_db)):
    invoice = await get_invoice(id, db)
    invoice.status = InvoiceStatusEnum.REJECTED
    db.add(AuditLog(
        invoice_id=id, actor="System User", target_type="INVOICE", target_id=invoice.invoice_number,
        action="HUMAN_REJECTED", details="Manually rejected by user."
    ))
    await db.commit()
    return {"message": "Rejected"}

from pydantic import BaseModel
class RequestInfoPayload(BaseModel):
    message: str

@router.post("/{id}/request-info")
async def request_info_invoice(id: int, payload: RequestInfoPayload, db: AsyncSession = Depends(get_db)):
    invoice = await get_invoice(id, db)
    invoice.status = InvoiceStatusEnum.INFORMATION_REQUESTED
    db.add(AuditLog(
        invoice_id=id, actor="System User", target_type="INVOICE", target_id=invoice.invoice_number,
        action="INFORMATION_REQUESTED", details=payload.message
    ))
    await db.commit()
    return {"message": "Information requested"}

from services.llm_service import llm_provider

@router.post("/{id}/explain")
async def explain_invoice(id: int, db: AsyncSession = Depends(get_db)):
    invoice = await get_invoice(id, db)
    if invoice.ai_explanation:
        return {"explanation": invoice.ai_explanation}
    
    # Prepare deterministic evidence
    evidence_parts = []
    for risk in invoice.risks:
        evidence_parts.append({
            "risk_type": risk.risk_type,
            "risk_level": risk.risk_level.value,
            "reason": risk.reason,
            "evidence": risk.evidence
        })
    
    risk_data = {
        "invoice_id": invoice.invoice_number,
        "vendor": invoice.vendor_name,
        "amount": invoice.total_amount,
        "risk_score": invoice.risk_score,
        "findings": evidence_parts
    }
    
    explanation = await llm_provider.explain_risk(risk_data, "finance employee")
    invoice.ai_explanation = explanation
    
    db.add(AuditLog(
        invoice_id=id, actor="System User", target_type="INVOICE", target_id=invoice.invoice_number,
        action="AI_EXPLANATION_GENERATED", details="User requested AI explanation."
    ))
    
    await db.commit()
    return {"explanation": explanation}

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(Invoice.id))) or 0
    auto_passed = await db.scalar(select(func.count(Invoice.id)).where(Invoice.status == InvoiceStatusEnum.AUTO_PASSED)) or 0
    human_review = await db.scalar(select(func.count(Invoice.id)).where(Invoice.status == InvoiceStatusEnum.HUMAN_REVIEW)) or 0
    high_risk = await db.scalar(select(func.count(Invoice.id)).where(Invoice.risk_level == RiskLevelEnum.HIGH)) or 0
    
    missing = await db.scalar(select(func.count(RiskResult.id)).where(RiskResult.risk_type == 'MISSING_FIELDS')) or 0
    dups = await db.scalar(select(func.count(RiskResult.id)).where(RiskResult.risk_type == 'DUPLICATE_INVOICE')) or 0
    anomalies = await db.scalar(select(func.count(RiskResult.id)).where(RiskResult.risk_type == 'VENDOR_PRICE_ANOMALY')) or 0
    splits = await db.scalar(select(func.count(RiskResult.id)).where(RiskResult.risk_type == 'POSSIBLE_INVOICE_SPLITTING')) or 0
    limit = await db.scalar(select(func.count(RiskResult.id)).where(RiskResult.risk_type == 'OVER_APPROVAL_LIMIT')) or 0
    
    po_mismatches = await db.scalar(select(func.count(RiskResult.id)).where(RiskResult.risk_type.in_(['PO_AMOUNT_MISMATCH', 'PO_VENDOR_MISMATCH', 'PO_NOT_FOUND']))) or 0
    policy_violations = await db.scalar(select(func.count(RiskResult.id)).where(RiskResult.risk_type == 'PO_REQUIRED_BUT_MISSING')) or 0

    return DashboardStats(
        total=total,
        auto_passed=auto_passed,
        human_review=human_review,
        high_risk=high_risk,
        missing_fields=missing,
        duplicates=dups,
        price_anomalies=anomalies,
        invoice_splitting=splits,
        over_limit=limit,
        po_mismatches=po_mismatches,
        policy_violations=policy_violations
    )


@router.get('/{id}/explain')
async def explain_invoice_risks(id: int, role: str = 'Finance Manager', db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == id).options(selectinload(Invoice.risks)))
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail='Invoice not found')
        
    risk_data = []
    for r in invoice.risks:
        risk_data.append({
            'risk_type': r.risk_type,
            'risk_level': r.risk_level.name,
            'reason': r.reason,
            'evidence': r.evidence
        })
        
    from services.ai_explanation import generate_risk_explanation
    explanation = await generate_risk_explanation(risk_data, role)
    return {'explanation': explanation}
