from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ScopeSchema(BaseModel):
    company_wide: bool = Field(default=True, description="True if this rule applies to the whole company, False if scoped to specific department, category, or vendor.")
    department: Optional[str] = Field(default=None, description="The specific department this rule applies to, if any.")
    category: Optional[str] = Field(default=None, description="The specific procurement category (e.g. 'IT EQUIPMENT') this rule applies to, if any.")
    vendor: Optional[str] = Field(default=None, description="The specific vendor this rule applies to, if any.")

class ConditionAmountSchema(BaseModel):
    operator: Optional[str] = Field(default=None, description="e.g. '>', '<', '>='")
    value: Optional[float] = Field(default=None, description="The numerical threshold.")
    currency: Optional[str] = Field(default=None, description="The currency, e.g. 'INR'")

class ConditionSchema(BaseModel):
    amount: Optional[ConditionAmountSchema] = None
    type: Optional[str] = Field(default=None, description="The type of condition (e.g. 'price_variance', 'quantity_variance', 'amount_variance')")
    aggregation_window_days: Optional[int] = Field(default=None, description="The time window in days for invoice splitting rules.")

class ActionSchema(BaseModel):
    required: Optional[bool] = None
    max_deviation_percent: Optional[float] = Field(default=None, description="The maximum percentage tolerance allowed.")
    requires_approval_from: Optional[str] = Field(default=None, description="The role or title required for approval.")

class ExceptionSchema(BaseModel):
    exception_type: str = Field(description="The type of exception, e.g. 'EMERGENCY_PURCHASE'")
    condition: str = Field(description="The condition under which the exception applies.")
    requires_approval_from: Optional[str] = Field(default=None, description="Who must approve the exception, if anyone.")

class SourceSchema(BaseModel):
    original_text: str = Field(description="The exact text snippet from the document that generated this rule.")
    section: Optional[str] = Field(default=None, description="The heading or section where the rule was found.")

class LLMPolicyRule(BaseModel):
    rule_type: str = Field(description="Must map to the risk engine. Allowed values: PO_REQUIRED, TOLERANCE, INVOICE_SPLITTING, APPROVAL_LIMIT, EXACT_DUPLICATE, VENDOR_PRICE_ANOMALY, CUSTOM_POLICY_RULE")
    scope: ScopeSchema
    conditions: Optional[ConditionSchema] = None
    action: Optional[ActionSchema] = None
    exceptions: List[ExceptionSchema] = Field(default_factory=list)
    confidence: float = Field(description="Confidence score from 0.0 to 1.0 that this rule is correctly extracted.")
    source: SourceSchema

class LLMPolicyResponse(BaseModel):
    document_summary: str = Field(description="A brief summary of what this document covers.")
    rules: List[LLMPolicyRule] = Field(description="The financial rules extracted from the document.")
