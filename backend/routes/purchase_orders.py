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
from models.models import PurchaseOrder, PurchaseOrderItem
from schemas.schemas import PurchaseOrderSchema
from services.azure_document_intelligence import analyze_purchase_order_bytes

router = APIRouter(prefix="/api/purchase-orders", tags=["purchase-orders"])

progress_queues = {}

async def process_po_zip_task(task_id: str, zip_bytes: bytes):
    queue = progress_queues.get(task_id)
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            valid_exts = ('.pdf', '.jpg', '.jpeg', '.png')
            files = [f for f in z.namelist() if f.lower().endswith(valid_exts) and not f.startswith('__MACOSX/')]
            
            total = len(files)
            if queue:
                await queue.put({"type": "start", "total": total})

            processed = 0
            stats = {"SUCCESS": 0, "FAILED": 0}
            semaphore = asyncio.Semaphore(10)
            
            async def process_file(filename):
                nonlocal processed
                file_data = z.read(filename)
                try:
                    async with semaphore:
                        extracted = await analyze_purchase_order_bytes(file_data)
                    
                    async with AsyncSessionLocal() as session:
                        import datetime
                        import re

                        def parse_date(date_val):
                            if not date_val: return None
                            if isinstance(date_val, str):
                                try: return datetime.datetime.fromisoformat(date_val.split('T')[0])
                                except ValueError: return None
                            if type(date_val) is datetime.date:
                                return datetime.datetime.combine(date_val, datetime.datetime.min.time())
                            return date_val

                        po_num = extracted.get("po_number")
                        vendor_raw = extracted.get("vendor_name")
                        
                        norm_vendor = None
                        if vendor_raw:
                            norm_vendor = re.sub(r'[^a-z0-9]', '', vendor_raw.lower().strip())
                        
                        if po_num:
                            existing_stmt = select(PurchaseOrder).where(PurchaseOrder.po_number == po_num)
                            existing_res = await session.execute(existing_stmt)
                            if existing_res.scalars().first():
                                raise Exception(f"DUPLICATE_PO: PO number {po_num} already exists.")

                        # Optional math validation
                        calc_sub = 0.0
                        items_data = extracted.get("items", [])
                        for item in items_data:
                            qty = item.get("quantity") or 0.0
                            up = item.get("unit_price") or 0.0
                            lt = item.get("line_total")
                            if lt is None and qty and up:
                                lt = qty * up
                                item["line_total"] = lt
                            calc_sub += (lt or 0.0)

                        new_po = PurchaseOrder(
                            po_number=po_num,
                            po_date=parse_date(extracted.get("po_date")),
                            vendor_name=vendor_raw,
                            normalized_vendor=norm_vendor,
                            department=extracted.get("department"),
                            subtotal=extracted.get("subtotal") or calc_sub,
                            tax=extracted.get("tax") or 0.0,
                            total_amount=extracted.get("total_amount") or (calc_sub + (extracted.get("tax") or 0.0)),
                            source_file=filename,
                            extraction_confidence=extracted.get("extraction_confidence")
                        )
                        session.add(new_po)
                        await session.flush()
                        
                        for item in items_data:
                            desc = item.get("description")
                            norm_desc = re.sub(r'[^a-z0-9]', '', desc.lower().strip()) if desc else None
                            session.add(PurchaseOrderItem(
                                po_id=new_po.id,
                                description=desc,
                                normalized_description=norm_desc,
                                quantity=item.get("quantity"),
                                unit_price=item.get("unit_price"),
                                line_total=item.get("line_total")
                            ))
                        
                        await session.commit()
                    stats["SUCCESS"] += 1
                except Exception as e:
                    stats["FAILED"] += 1
                    print(f"Error processing PO {filename}: {e}")
                
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
        import traceback
        with open("fatal_error.txt", "a") as f:
            f.write("PO TASK FATAL:\n" + traceback.format_exc() + "\n")
        if queue:
            await queue.put({"type": "error", "message": str(e)})
    finally:
        if queue:
            await queue.put(None)

@router.post("/upload-zip")
async def upload_po_zip(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Must be a ZIP file")
    
    zip_bytes = await file.read()
    task_id = str(uuid.uuid4())
    progress_queues[task_id] = asyncio.Queue()
    background_tasks.add_task(process_po_zip_task, task_id, zip_bytes)
    return {"task_id": task_id}

@router.get("/progress/{task_id}")
async def get_po_progress(task_id: str):
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

@router.get("", response_model=list[PurchaseOrderSchema])
async def get_purchase_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PurchaseOrder).options(selectinload(PurchaseOrder.items)))
    return result.scalars().all()
