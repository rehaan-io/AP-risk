import re

with open("backend/routes/invoices.py", "r") as f:
    content = f.read()

new_routes = """@router.post("/{id}/approve")
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
    return {"explanation": explanation}"""

content = re.sub(
    r'@router\.post\("/\{id\}/approve"\).*?return \{"message": "Rejected"\}', 
    new_routes.strip(), 
    content, 
    flags=re.DOTALL
)

with open("backend/routes/invoices.py", "w") as f:
    f.write(content)
