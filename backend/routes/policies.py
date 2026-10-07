import uuid
import asyncio
import io
import zipfile
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from starlette.responses import StreamingResponse

from database import get_db, AsyncSessionLocal
from models.models import PolicyDocument, PolicyRule, PolicyRuleStatus, PolicyRuleReview
from schemas.schemas import PolicyDocumentSchema, PolicyRuleSchema
from services.policy_extractor import extract_and_interpret_policy

router = APIRouter(prefix="/api/policies", tags=["policies"])

progress_queues = {}

async def process_policy_zip_task(task_id: str, zip_bytes: bytes):
    queue = progress_queues.get(task_id)
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            valid_exts = ('.pdf', '.jpg', '.jpeg', '.png', '.docx', '.txt', '.xlsx')
            files = [f for f in z.namelist() if f.lower().endswith(valid_exts) and not f.startswith('__MACOSX/')]
            
            total = len(files)
            if queue:
                await queue.put({"type": "start", "total": total})

            processed = 0
            stats = {"SUCCESS": 0, "FAILED": 0, "RULES_EXTRACTED": 0}
            semaphore = asyncio.Semaphore(5) # Lower concurrency for LLM limits
            
            async def process_file(filename):
                nonlocal processed
                file_data = z.read(filename)
                try:
                    async with semaphore:
                        text, rules = await extract_and_interpret_policy(filename, file_data)
                    
                    async with AsyncSessionLocal() as session:
                        doc = PolicyDocument(
                            filename=filename,
                            extracted_text=text
                        )
                        session.add(doc)
                        await session.flush()
                        
                        for rule_data in rules:
                            # Handle source field
                            source_obj = rule_data.get("source", {})
                            original_text = source_obj.get("original_text", "")
                            
                            combined_source = filename
                            if original_text:
                                combined_source = f"{filename} | Snippet: \"{original_text[:150]}\""

                            rule = PolicyRule(
                                document_id=doc.id,
                                rule_type=rule_data.get("rule_type", "CUSTOM_POLICY_RULE"),
                                scope=rule_data.get("scope"),
                                conditions=rule_data.get("conditions"),
                                action=rule_data.get("action"),
                                exceptions=rule_data.get("exceptions"),
                                confidence=rule_data.get("confidence", 0.9),
                                requires_confirmation=True, # LLM generated rules always require confirmation initially
                                status=PolicyRuleStatus.PENDING_REVIEW,
                                source_page=combined_source
                            )
                            session.add(rule)
                            stats["RULES_EXTRACTED"] += 1
                        
                        await session.commit()
                    stats["SUCCESS"] += 1
                except Exception as e:
                    stats["FAILED"] += 1
                    print(f"Error processing Policy {filename}: {e}")
                
                processed += 1
                if queue:
                    await queue.put({
                        "type": "progress", 
                        "processed": processed, 
                        "total": total, 
                        "current": filename
                    })

            tasks = [process_file(f) for f in files]
            await asyncio.gather(*tasks)

            if queue:
                await queue.put({"type": "complete", "total": total, "stats": stats})

    except Exception as e:
        if queue:
            await queue.put({"type": "error", "message": str(e)})
    finally:
        if queue:
            await queue.put(None)

@router.post("/upload-zip")
async def upload_policy_zip(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Must be a ZIP file")
    
    zip_bytes = await file.read()
    task_id = str(uuid.uuid4())
    progress_queues[task_id] = asyncio.Queue()
    background_tasks.add_task(process_policy_zip_task, task_id, zip_bytes)
    return {"task_id": task_id}

@router.get("/progress/{task_id}")
async def get_policy_progress(task_id: str):
    queue = progress_queues.get(task_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        try:
            while True:
                data = await queue.get()
                if data is None: break
                import json
                yield f"data: {json.dumps(data)}\n\n"
        finally:
            if task_id in progress_queues:
                del progress_queues[task_id]
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("", response_model=list[PolicyDocumentSchema])
async def get_policies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PolicyDocument).options(selectinload(PolicyDocument.rules)))
    return result.scalars().all()

@router.get("/rules", response_model=list[PolicyRuleSchema])
async def get_policy_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PolicyRule))
    return result.scalars().all()

@router.post("/rules/{id}/approve")
async def approve_rule(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PolicyRule).where(PolicyRule.id == id))
    rule = result.scalars().first()
    if not rule: raise HTTPException(status_code=404)
    rule.status = PolicyRuleStatus.ACTIVE
    review = PolicyRuleReview(rule_id=id, action="APPROVED", reviewer="System User")
    db.add(review)
    await db.commit()
    return {"message": "Approved"}

@router.post("/rules/{id}/reject")
async def reject_rule(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PolicyRule).where(PolicyRule.id == id))
    rule = result.scalars().first()
    if not rule: raise HTTPException(status_code=404)
    rule.status = PolicyRuleStatus.REJECTED
    review = PolicyRuleReview(rule_id=id, action="REJECTED", reviewer="System User")
    db.add(review)
    await db.commit()
    return {"message": "Rejected"}
