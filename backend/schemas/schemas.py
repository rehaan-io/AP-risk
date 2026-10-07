from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import datetime
from models.models import RiskLevelEnum, InvoiceStatusEnum

class InvoiceItemSchema(BaseModel):
    id: int
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)

class RiskResultSchema(BaseModel):
    id: int
    risk_type: str
    risk_level: RiskLevelEnum
    reason: str
    evidence: Optional[str] = None
    recommended_action: Optional[str] = None
    confidence: Optional[float] = None
    score_contribution: Optional[float] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AuditLogSchema(BaseModel):
    id: int
    invoice_id: Optional[int] = None
    actor: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    action: str
    details: Optional[str] = None
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

class InvoiceSchema(BaseModel):
    id: int
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    invoice_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    po_number: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    payment_terms: Optional[str] = None
    status: InvoiceStatusEnum
    risk_level: RiskLevelEnum
    risk_score: Optional[float] = None
    confidence: Optional[float] = None
    ai_explanation: Optional[str] = None
    created_at: datetime
    
    items: List[InvoiceItemSchema] = []
    risks: List[RiskResultSchema] = []
    logs: List[AuditLogSchema] = []
    
    model_config = ConfigDict(from_attributes=True)

class DashboardStats(BaseModel):
    total: int
    auto_passed: int
    human_review: int
    high_risk: int
    missing_fields: int
    duplicates: int
    price_anomalies: int
    invoice_splitting: int
    over_limit: int
    po_mismatches: int
    policy_violations: int


class PurchaseOrderItemSchema(BaseModel):
    id: int
    description: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    line_total: Optional[float] = None
    unit: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class PurchaseOrderSchema(BaseModel):
    id: int
    po_number: Optional[str] = None
    po_date: Optional[datetime] = None
    vendor_name: Optional[str] = None
    department: Optional[str] = None
    requester: Optional[str] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    approval_status: Optional[str] = None
    approval_date: Optional[datetime] = None
    subtotal: Optional[float] = None
    discount: Optional[float] = None
    tax: Optional[float] = None
    total_amount: Optional[float] = None
    payment_terms: Optional[str] = None
    source_file: Optional[str] = None
    created_at: datetime
    
    items: List[PurchaseOrderItemSchema] = []
    
    model_config = ConfigDict(from_attributes=True)

class PolicyRuleSchema(BaseModel):
    id: int
    rule_type: str
    scope: Optional[Dict[str, Any]] = None
    conditions: Optional[Dict[str, Any]] = None
    action: Optional[Dict[str, Any]] = None
    exceptions: Optional[List[Dict[str, Any]]] = None
    priority: Optional[int] = None
    source_page: Optional[str] = None
    source_sheet: Optional[str] = None
    confidence: Optional[float] = None
    requires_confirmation: bool
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PolicyDocumentSchema(BaseModel):
    id: int
    filename: str
    created_at: datetime
    rules: List[PolicyRuleSchema] = []
    
    model_config = ConfigDict(from_attributes=True)


class PolicyScope(BaseModel):
    company_wide: bool = True
    department: Optional[str] = None
    category: Optional[str] = None
    vendor: Optional[str] = None

class PolicyException(BaseModel):
    exception_type: str
    condition: str
    requires_approval_from: Optional[str] = None

class PolicySource(BaseModel):
    document_name: Optional[str] = None
    page_or_sheet: Optional[str] = None
    section: Optional[str] = None
    original_text: Optional[str] = None

class PolicyRuleOutputSchema(BaseModel):
    rule_type: str
    scope: Optional[PolicyScope] = None
    conditions: Optional[Dict[str, Any]] = None
    action: Optional[Dict[str, Any]] = None
    exceptions: Optional[List[PolicyException]] = None
    confidence: Optional[float] = None
    source: Optional[PolicySource] = None
