import os
import io
import asyncio
from typing import Dict, Any
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from dotenv import load_dotenv

load_dotenv()

AZURE_DI_ENDPOINT = os.getenv("AZURE_DI_ENDPOINT", "")
AZURE_DI_KEY = os.getenv("AZURE_DI_KEY", "")

async def analyze_invoice_bytes(file_bytes: bytes) -> Dict[str, Any]:
    if not AZURE_DI_ENDPOINT or not AZURE_DI_KEY:
        raise ValueError("Azure Document Intelligence credentials are not configured.")

    client = DocumentIntelligenceClient(
        endpoint=AZURE_DI_ENDPOINT,
        credential=AzureKeyCredential(AZURE_DI_KEY)
    )

    async with client:
        # Use begin_analyze_document directly with bytes
        poller = await client.begin_analyze_document(
            model_id="prebuilt-invoice",
            body=file_bytes,
            content_type="application/octet-stream"
        )
        
        # Wait for the result
        result: AnalyzeResult = await poller.result()

    return _normalize_azure_result(result)

def _normalize_azure_result(result: AnalyzeResult) -> Dict[str, Any]:
    # Extract the first document's fields
    if not result.documents:
        return {}

    doc = result.documents[0]
    fields = doc.fields or {}

    def get_field_value(field_name: str, default=None):
        if field_name in fields:
            field = fields[field_name]
            return field.get('valueString') or field.get('valueDate') or field.get('valueNumber') or field.get('content')
        return default
        
    def get_field_float(field_name: str, default=None):
        if field_name in fields:
            field = fields[field_name]
            val = field.get('valueNumber') or field.get('valueCurrency', {}).get('amount')
            if val is not None:
                return float(val)
        return default

    normalized = {
        "vendor_name": get_field_value("VendorName"),
        "vendor_address": get_field_value("VendorAddress"),
        "invoice_number": get_field_value("InvoiceId"),
        "invoice_date": get_field_value("InvoiceDate"),
        "due_date": get_field_value("DueDate"),
        "po_number": get_field_value("PurchaseOrder"),
        "subtotal": get_field_float("SubTotal"),
        "tax": get_field_float("TotalTax"),
        "total_amount": get_field_float("InvoiceTotal"),
        "currency": get_field_value("InvoiceTotal", {}), # Azure might pack currency differently, simplification for now
        "payment_terms": get_field_value("PaymentTerm"),
        "items": []
    }

    # Extract items
    if "Items" in fields:
        items_field = fields["Items"]
        if items_field.get('valueArray'):
            for item in items_field['valueArray']:
                item_fields = item.get('valueObject', {})
                desc = item_fields.get("Description", {}).get("valueString") or item_fields.get("Description", {}).get("content")
                qty = item_fields.get("Quantity", {}).get("valueNumber")
                unit_price = item_fields.get("UnitPrice", {}).get("valueNumber") or item_fields.get("UnitPrice", {}).get("valueCurrency", {}).get("amount")
                amount = item_fields.get("Amount", {}).get("valueNumber") or item_fields.get("Amount", {}).get("valueCurrency", {}).get("amount")

                normalized["items"].append({
                    "description": desc,
                    "quantity": float(qty) if qty is not None else None,
                    "unit_price": float(unit_price) if unit_price is not None else None,
                    "amount": float(amount) if amount is not None else None
                })

    return normalized

async def analyze_purchase_order_bytes(file_bytes: bytes) -> Dict[str, Any]:
    if not AZURE_DI_ENDPOINT or not AZURE_DI_KEY:
        raise ValueError('Azure Document Intelligence credentials are not configured.')

    client = DocumentIntelligenceClient(
        endpoint=AZURE_DI_ENDPOINT,
        credential=AzureKeyCredential(AZURE_DI_KEY)
    )

    async with client:
        # Prebuilt PO model might not be natively supported in all regions, we will use prebuilt-document as fallback if it fails, but let's try prebuilt-invoice as a fallback to extract structured fields if needed, or prebuilt-purchaseOrder if it exists.
        # Actually Azure has 'prebuilt-purchaseOrder'. Let's use it.
        poller = await client.begin_analyze_document(
            model_id='prebuilt-invoice', # Using prebuilt-invoice as standard if PO fails, but we'll try prebuilt-invoice since it handles PO-like docs well for vendors, totals, etc. Wait, let's use 'prebuilt-document' and parse KVP. Or 'prebuilt-invoice' is better. Let's stick to 'prebuilt-invoice' as requested or fallback.
            body=file_bytes,
            content_type='application/octet-stream'
        )
        result: AnalyzeResult = await poller.result()

    return _normalize_po_azure_result(result)

def _normalize_po_azure_result(result: AnalyzeResult) -> Dict[str, Any]:
    if not result.documents:
        return {}

    doc = result.documents[0]
    fields = doc.fields or {}

    def get_val(field_name: str, default=None):
        if field_name in fields:
            f = fields[field_name]
            return f.get('valueString') or f.get('valueDate') or f.get('valueNumber') or f.get('content')
        return default
        
    def get_flt(field_name: str, default=None):
        if field_name in fields:
            f = fields[field_name]
            val = f.get('valueNumber') or f.get('valueCurrency', {}).get('amount')
            if val is not None: return float(val)
        return default

    normalized = {
        'po_number': get_val('PurchaseOrder') or get_val('InvoiceId'),
        'vendor_name': get_val('VendorName'),
        'po_date': get_val('InvoiceDate'),
        'department': None,
        'requester': None,
        'subtotal': get_flt('SubTotal'),
        'tax': get_flt('TotalTax'),
        'total_amount': get_flt('InvoiceTotal'),
        'items': [],
        'extraction_confidence': doc.confidence
    }

    if 'Items' in fields and fields['Items'].get('valueArray'):
        for item in fields['Items']['valueArray']:
            obj = item.get('valueObject', {})
            desc = obj.get('Description', {}).get('valueString') or obj.get('Description', {}).get('content')
            qty = obj.get('Quantity', {}).get('valueNumber')
            unit_price = obj.get('UnitPrice', {}).get('valueNumber') or obj.get('UnitPrice', {}).get('valueCurrency', {}).get('amount')
            amount = obj.get('Amount', {}).get('valueNumber') or obj.get('Amount', {}).get('valueCurrency', {}).get('amount')
            
            normalized['items'].append({
                'description': desc,
                'quantity': float(qty) if qty is not None else None,
                'unit_price': float(unit_price) if unit_price is not None else None,
                'line_total': float(amount) if amount is not None else None
            })

    return normalized

async def analyze_policy_bytes(file_bytes: bytes) -> str:
    if not AZURE_DI_ENDPOINT or not AZURE_DI_KEY:
        raise ValueError('Azure Document Intelligence credentials are not configured.')

    client = DocumentIntelligenceClient(
        endpoint=AZURE_DI_ENDPOINT,
        credential=AzureKeyCredential(AZURE_DI_KEY)
    )

    async with client:
        poller = await client.begin_analyze_document(
            model_id='prebuilt-read',
            body=file_bytes,
            content_type='application/octet-stream'
        )
        result: AnalyzeResult = await poller.result()

    return result.content
