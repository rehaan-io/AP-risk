import json
import re
import statistics
import datetime
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
from sqlalchemy.orm import selectinload
from typing import Dict, Any, List, Tuple
from difflib import SequenceMatcher
from models.models import Invoice, InvoiceItem, RiskLevelEnum, InvoiceStatusEnum, PurchaseOrder, PolicyRule, PolicyRuleStatus


def normalize_string(val: Any) -> str:
    if not val:
        return ''
    return re.sub(r'[^a-z0-9]', '', str(val).lower().strip())

def parse_date_robust(date_val: Any):
    if not date_val: return None
    if isinstance(date_val, str):
        try:
            return datetime.datetime.fromisoformat(date_val.split('T')[0])
        except ValueError:
            return None
    if type(date_val) is datetime.date:
        return datetime.datetime.combine(date_val, datetime.datetime.min.time())
    return date_val

def similar(a: str, b: str) -> float:
    if not a or not b: return 0.0
    return SequenceMatcher(None, a, b).ratio()

async def evaluate_invoice(db: AsyncSession, invoice_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], InvoiceStatusEnum, RiskLevelEnum, float, float]:
    findings = []
    total_risk_score = 0.0
    overall_confidence_sum = 0.0
    
    def add_finding(risk_type: str, severity: RiskLevelEnum, base_score: float, confidence: float, reason: str, facts: Dict[str, Any], supporting: List[Dict[str, Any]] = None) -> float:
        nonlocal total_risk_score, overall_confidence_sum
        
        contribution = base_score * confidence
        total_risk_score += contribution
        overall_confidence_sum += confidence
        
        evidence_obj = {
            'finding_id': f'F-{len(findings)+1}',
            'risk_type': risk_type,
            'severity': severity.name,
            'confidence': confidence,
            'subject': {'invoice_number': invoice_data.get('invoice_number')},
            'facts': facts,
            'supporting_records': supporting or [],
            'calculations': {'base_score': base_score, 'contribution': contribution}
        }
        
        findings.append({
            'risk_type': risk_type,
            'risk_level': severity,
            'reason': reason,
            'confidence': confidence,
            'score_contribution': contribution,
            'evidence': json.dumps(evidence_obj)
        })
        return contribution

    inv_num = invoice_data.get('invoice_number')
    norm_inv_num = normalize_string(inv_num)
    vendor = invoice_data.get('vendor_name')
    norm_vendor = normalize_string(vendor)
    po_number = invoice_data.get('po_number')
    norm_po_number = normalize_string(po_number)
    total = invoice_data.get('total_amount') or 0.0
    inv_date = parse_date_robust(invoice_data.get('invoice_date'))
    department = invoice_data.get('department')
    category = invoice_data.get('category')
    items = invoice_data.get('items', [])

    stmt_policies = select(PolicyRule).where(PolicyRule.status == PolicyRuleStatus.ACTIVE).order_by(PolicyRule.priority.asc().nulls_last())
    res_policies = await db.execute(stmt_policies)
    active_policies = res_policies.scalars().all()

    default_limit = 100000.0
    active_limit = default_limit
    po_required = False
    quantity_tolerance = 0.05
    price_tolerance = 0.10
    split_window_days = 7

    for rule in active_policies:
        scope = rule.scope or {}
        if scope.get('department') and scope.get('department') != department: continue
        if scope.get('category') and scope.get('category') != category: continue
        if scope.get('vendor') and scope.get('vendor') != vendor: continue
        
        rt = rule.rule_type
        cond = rule.conditions or {}
        act = rule.action or {}
        
        if rt == 'APPROVAL_LIMIT':
            val = cond.get('amount', {}).get('value')
            if val: active_limit = min(active_limit, float(val))
        elif rt == 'PO_REQUIRED':
            amt_val = cond.get('amount', {}).get('value')
            if amt_val and total > float(amt_val):
                po_required = True
        elif rt == 'TOLERANCE':
            act_dev = act.get('max_deviation_percent')
            if cond.get('type') == 'QUANTITY' and act_dev is not None:
                quantity_tolerance = float(act_dev) / 100.0
            elif cond.get('type') == 'PRICE' and act_dev is not None:
                price_tolerance = float(act_dev) / 100.0
        elif rt == 'SPLIT_INVOICE_REVIEW':
            win = cond.get('aggregation_window_days')
            if win: split_window_days = int(win)

    missing = []
    if not inv_num: missing.append('invoice_number')
    if not vendor: missing.append('vendor_name')
    if not total: missing.append('total_amount')
    if missing:
        add_finding('MISSING_FIELDS', RiskLevelEnum.MEDIUM, 20.0, 1.0, f"Missing critical fields: {', '.join(missing)}", {'missing': missing})

    calc_subtotal = 0.0
    math_errors = []
    for idx, itm in enumerate(items):
        q = itm.get('quantity')
        up = itm.get('unit_price')
        amt = itm.get('amount')
        if q and up and amt:
            exp = q * up
            if abs(exp - amt) > 1.0:
                math_errors.append({'line': idx, 'expected': exp, 'actual': amt, 'diff': abs(exp - amt)})
        calc_subtotal += (amt or 0.0)

    if math_errors:
        add_finding('CALCULATION_MISMATCH', RiskLevelEnum.MEDIUM, 25.0, 0.95, 'Line item math does not match expected (qty * price).', {'errors': math_errors})

    if inv_num and norm_vendor:
        dup_stmt = select(Invoice).where(
            or_(
                Invoice.normalized_invoice_number == norm_inv_num,
                Invoice.normalized_vendor == norm_vendor
            )
        )
        dup_res = await db.execute(dup_stmt)
        candidates = dup_res.scalars().all()
        
        for cand in candidates:
            dup_score = 0.0
            is_exact_inv = (cand.normalized_invoice_number == norm_inv_num)
            ven_sim = similar(cand.normalized_vendor, norm_vendor)
            is_exact_ven = (ven_sim > 0.95)
            
            if is_exact_inv: dup_score += 40.0
            if is_exact_ven: 
                dup_score += 20.0
            elif ven_sim > 0.8:
                dup_score += 10.0
                
            if po_number and cand.po_number and similar(normalize_string(cand.po_number), norm_po_number) > 0.9:
                dup_score += 15.0
            if cand.total_amount and abs(cand.total_amount - total) < 1.0:
                dup_score += 15.0
            if inv_date and cand.invoice_date and abs((inv_date - cand.invoice_date).days) <= 1:
                dup_score += 10.0
                
            if dup_score >= 80.0:
                add_finding('EXACT_DUPLICATE', RiskLevelEnum.CRITICAL, 60.0, 0.99, 'Exact duplicate invoice detected.', {'similarity_score': dup_score, 'matched_fields': ['invoice_number' if is_exact_inv else '', 'vendor' if is_exact_ven else '']}, [{'type': 'INVOICE', 'id': cand.id}])
                break
            elif dup_score >= 50.0:
                add_finding('HIGH_PROBABILITY_DUPLICATE', RiskLevelEnum.HIGH, 40.0, 0.85, 'High probability duplicate detected.', {'similarity_score': dup_score}, [{'type': 'INVOICE', 'id': cand.id}])
            elif dup_score >= 35.0:
                add_finding('POSSIBLE_DUPLICATE', RiskLevelEnum.MEDIUM, 25.0, 0.60, 'Possible duplicate detected.', {'similarity_score': dup_score}, [{'type': 'INVOICE', 'id': cand.id}])

    if total > active_limit:
        add_finding('OVER_APPROVAL_LIMIT', RiskLevelEnum.HIGH, 40.0, 1.0, f'Exceeds active approval limit of {active_limit}', {'limit': active_limit, 'invoice_amount': total})

    if po_required and not po_number:
        add_finding('PO_REQUIRED_BUT_MISSING', RiskLevelEnum.HIGH, 45.0, 1.0, 'Company policy requires a PO for this invoice amount/category.', {'invoice_amount': total, 'po_required_flag': True})

    if po_number:
        po_stmt = select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.po_number == po_number)
        po_res = await db.execute(po_stmt)
        po = po_res.scalars().first()
        
        po_penalty = 0.0
        
        if not po:
            add_finding('PO_NOT_FOUND', RiskLevelEnum.MEDIUM, 25.0, 1.0, f'PO {po_number} referenced but not found.', {'po_number': po_number})
        else:
            ven_sim = similar(norm_vendor, po.normalized_vendor) if norm_vendor and po.normalized_vendor else 0
            if ven_sim < 0.7:
                po_penalty += add_finding('PO_VENDOR_MISMATCH', RiskLevelEnum.HIGH, 40.0, 0.9, 'Invoice vendor does not match PO vendor.', {'invoice_vendor': norm_vendor, 'po_vendor': po.normalized_vendor, 'similarity': ven_sim}, [{'type': 'PO', 'id': po.id}])
            
            if po.total_amount and abs(total - po.total_amount) > 1.0:
                dev = abs(total - po.total_amount) / po.total_amount if po.total_amount > 0 else 0
                if dev > 0.03: 
                    po_penalty += add_finding('PO_AMOUNT_MISMATCH', RiskLevelEnum.HIGH, 35.0, 0.95, 'Invoice total differs from PO total.', {'invoice_total': total, 'po_total': po.total_amount, 'diff': abs(total - po.total_amount)}, [{'type': 'PO', 'id': po.id}])

            if po.items and items:
                unmatched = 0
                for inv_itm in items:
                    inv_desc = normalize_string(inv_itm.get('description'))
                    inv_qty = inv_itm.get('quantity') or 0.0
                    inv_up = inv_itm.get('unit_price') or 0.0
                    
                    best_po_itm = None
                    best_sim = 0
                    for po_itm in po.items:
                        po_desc = po_itm.normalized_description or ''
                        sim = similar(inv_desc, po_desc)
                        if sim > best_sim:
                            best_sim = sim
                            best_po_itm = po_itm
                            
                    if best_po_itm and best_sim > 0.6:
                        po_q = best_po_itm.quantity or 0.0
                        if inv_qty > po_q * (1.0 + quantity_tolerance):
                            po_penalty += add_finding('PO_QUANTITY_EXCEEDED', RiskLevelEnum.HIGH, 30.0, 0.9, f'Invoice quantity {inv_qty} exceeds PO quantity {po_q} beyond {quantity_tolerance*100}% tolerance.', {'item': inv_itm.get('description'), 'inv_qty': inv_qty, 'po_qty': po_q}, [{'type': 'PO_ITEM', 'id': best_po_itm.id}])
                        
                        po_up = best_po_itm.unit_price or 0.0
                        if po_up > 0 and inv_up > po_up * (1.0 + price_tolerance):
                            po_penalty += add_finding('PO_UNIT_PRICE_MISMATCH', RiskLevelEnum.HIGH, 30.0, 0.9, f'Invoice unit price {inv_up} exceeds PO unit price {po_up}.', {'item': inv_itm.get('description'), 'inv_up': inv_up, 'po_up': po_up}, [{'type': 'PO_ITEM', 'id': best_po_itm.id}])
                    else:
                        unmatched += 1
                if unmatched > 0:
                    po_penalty += add_finding('PO_ITEM_MISMATCH', RiskLevelEnum.MEDIUM, 20.0, 0.8, f'{unmatched} items could not be linked to the PO.', {'unmatched_count': unmatched}, [{'type': 'PO', 'id': po.id}])
                    
            if po_penalty > 60.0:
                reduction = po_penalty - 60.0
                total_risk_score -= reduction 

    if norm_vendor and inv_date:
        split_thresh = inv_date - timedelta(days=split_window_days)
        split_stmt = select(Invoice.id, Invoice.total_amount).where(
            Invoice.normalized_vendor == norm_vendor,
            Invoice.invoice_date >= split_thresh,
            Invoice.invoice_date <= inv_date
        )
        split_res = await db.execute(split_stmt)
        cluster = split_res.fetchall()
        
        cluster_sum = sum(c[1] for c in cluster if c[1] is not None) + total
        if total < active_limit and cluster_sum > active_limit:
            add_finding('POSSIBLE_INVOICE_SPLITTING', RiskLevelEnum.HIGH, 40.0, 0.85, f'Related invoices within {split_window_days} days exceed approval limit.', {'cluster_sum': cluster_sum, 'limit': active_limit, 'time_window': split_window_days}, [{'type': 'INVOICE', 'id': c[0]} for c in cluster])

    if norm_vendor:
        for idx, itm in enumerate(items):
            desc = itm.get('description')
            norm_desc = normalize_string(desc)
            price = itm.get('unit_price')
            if norm_desc and price:
                price_stmt = select(InvoiceItem.unit_price, Invoice.id).join(Invoice).where(
                    Invoice.normalized_vendor == norm_vendor,
                    InvoiceItem.normalized_description == norm_desc
                ).order_by(Invoice.created_at.desc()).limit(10)
                
                price_res = await db.execute(price_stmt)
                history = price_res.fetchall()
                valid_prices = [h[0] for h in history if h[0] is not None]
                
                if len(valid_prices) >= 3:
                    med_price = statistics.median(valid_prices)
                    mad = statistics.median([abs(p - med_price) for p in valid_prices])
                    if mad == 0: mad = med_price * 0.05 
                    
                    diff = price - med_price
                    dev_pct = (diff / med_price * 100) if med_price > 0 else 0
                    
                    if diff > 0 and diff > (mad * 3) and dev_pct > (price_tolerance * 100):
                        add_finding('VENDOR_PRICE_ANOMALY', RiskLevelEnum.HIGH, 35.0, 0.90, f'Unit price {price} is an outlier compared to historical median {med_price:.2f}.', {'current': price, 'median': med_price, 'mad': mad, 'dev_pct': dev_pct, 'history_size': len(valid_prices)}, [{'type': 'INVOICE', 'id': h[1]} for h in history])

    avg_conf = overall_confidence_sum / len(findings) if findings else 1.0
    
    if total_risk_score == 0:
        status = InvoiceStatusEnum.AUTO_PASSED
        final_level = RiskLevelEnum.LOW
    else:
        status = InvoiceStatusEnum.HUMAN_REVIEW
        if total_risk_score < 25:
            final_level = RiskLevelEnum.LOW
        elif total_risk_score < 50:
            final_level = RiskLevelEnum.MEDIUM
        elif total_risk_score < 75:
            final_level = RiskLevelEnum.HIGH
        else:
            final_level = RiskLevelEnum.CRITICAL
            
    return findings, status, final_level, total_risk_score, avg_conf
