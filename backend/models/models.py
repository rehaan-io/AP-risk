from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, Boolean, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base

class RiskLevelEnum(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class InvoiceStatusEnum(enum.Enum):
    AUTO_PASSED = "AUTO_PASSED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    INFORMATION_REQUESTED = "INFORMATION_REQUESTED"

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, index=True, nullable=True)
    normalized_invoice_number = Column(String, index=True, nullable=True)
    vendor_name = Column(String, index=True, nullable=True)
    normalized_vendor = Column(String, index=True, nullable=True)
    vendor_address = Column(String, nullable=True)
    invoice_date = Column(DateTime, index=True, nullable=True)
    due_date = Column(DateTime, nullable=True)
    po_number = Column(String, index=True, nullable=True)
    department = Column(String, nullable=True)
    category = Column(String, nullable=True)
    subtotal = Column(Float, nullable=True)
    tax = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    payment_terms = Column(String, nullable=True)
    status = Column(Enum(InvoiceStatusEnum), default=InvoiceStatusEnum.HUMAN_REVIEW)
    risk_level = Column(Enum(RiskLevelEnum), default=RiskLevelEnum.LOW)
    risk_score = Column(Float, default=0.0)
    confidence = Column(Float, default=1.0)
    ai_explanation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    risks = relationship("RiskResult", back_populates="invoice", cascade="all, delete-orphan")
    logs = relationship("AuditLog", back_populates="invoice", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_invoice_norm_vendor_date', 'normalized_vendor', 'invoice_date'),
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), index=True)
    description = Column(String, nullable=True)
    normalized_description = Column(String, index=True, nullable=True)
    quantity = Column(Float, nullable=True)
    unit_price = Column(Float, nullable=True)
    amount = Column(Float, nullable=True)

    invoice = relationship("Invoice", back_populates="items")


class RiskResult(Base):
    __tablename__ = "risk_results"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), index=True)
    risk_type = Column(String, index=True)
    risk_level = Column(Enum(RiskLevelEnum), index=True)
    reason = Column(Text)
    evidence = Column(Text, nullable=True)  # JSON string or plain text
    recommended_action = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)
    score_contribution = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="risks")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), index=True, nullable=True) # made nullable for general events
    actor = Column(String, default="System")
    target_type = Column(String, nullable=True)
    target_id = Column(String, nullable=True)
    action = Column(String, index=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="logs")


class PolicyRuleStatus(enum.Enum):
    PENDING_REVIEW = 'PENDING_REVIEW'
    ACTIVE = 'ACTIVE'
    REJECTED = 'REJECTED'

class PurchaseOrder(Base):
    __tablename__ = 'purchase_orders'

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String, index=True, nullable=True)
    po_date = Column(DateTime, nullable=True)
    vendor_name = Column(String, index=True, nullable=True)
    normalized_vendor = Column(String, index=True, nullable=True)
    vendor_id = Column(String, nullable=True)
    department = Column(String, nullable=True)
    requester = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    status = Column(String, nullable=True)
    approval_status = Column(String, nullable=True)
    approval_date = Column(DateTime, nullable=True)
    subtotal = Column(Float, nullable=True)
    discount = Column(Float, nullable=True)
    tax = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=True)
    payment_terms = Column(String, nullable=True)
    delivery_date = Column(DateTime, nullable=True)
    source_file = Column(String, nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    items = relationship('PurchaseOrderItem', back_populates='purchase_order', cascade='all, delete-orphan')

class PurchaseOrderItem(Base):
    __tablename__ = 'purchase_order_items'

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey('purchase_orders.id'), index=True)
    description = Column(String, nullable=True)
    normalized_description = Column(String, index=True, nullable=True)
    category = Column(String, nullable=True)
    quantity = Column(Float, nullable=True)
    unit_price = Column(Float, nullable=True)
    line_total = Column(Float, nullable=True)
    unit = Column(String, nullable=True)

    purchase_order = relationship('PurchaseOrder', back_populates='items')

class PolicyDocument(Base):
    __tablename__ = 'policies'

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    extracted_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    rules = relationship('PolicyRule', back_populates='document', cascade='all, delete-orphan')

class PolicyRule(Base):
    __tablename__ = 'policy_rules'

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('policies.id'), index=True)
    rule_type = Column(String, index=True, nullable=False)
    scope = Column(JSON, nullable=True)
    conditions = Column(JSON, nullable=True)
    action = Column(JSON, nullable=True)
    exceptions = Column(JSON, nullable=True)
    priority = Column(Integer, nullable=True)
    source_page = Column(String, nullable=True)
    source_sheet = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    requires_confirmation = Column(Boolean, default=True)
    status = Column(Enum(PolicyRuleStatus), default=PolicyRuleStatus.PENDING_REVIEW)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship('PolicyDocument', back_populates='rules')
    reviews = relationship('PolicyRuleReview', back_populates='rule', cascade='all, delete-orphan')

class PolicyRuleReview(Base):
    __tablename__ = 'policy_rule_reviews'

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey('policy_rules.id'), index=True)
    action = Column(String, nullable=False) # APPROVED, REJECTED, EDITED
    reviewer = Column(String, nullable=True)
    edits = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    rule = relationship('PolicyRule', back_populates='reviews')


class AppConfiguration(Base):
    __tablename__ = 'app_configuration'
    
    id = Column(Integer, primary_key=True, index=True) # Always 1
    policy_mode = Column(String, default='PENDING') # PENDING, COMPANY_POLICY, DEFAULT_POLICY
    po_mode = Column(String, default='PENDING') # PENDING, USES_PO, NO_PO
    setup_completed = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

