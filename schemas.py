"""
Data models and schemas for the Chartered Accountant (CA) Agent.
Equipped with dynamic Pydantic / dataclasses fallback for instant zero-dependency execution.
"""
from typing import List, Optional, Any, Dict

try:
    from pydantic import BaseModel, Field
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump(self) -> Dict[str, Any]:
            res = {}
            for k, v in self.__dict__.items():
                if isinstance(v, list):
                    res[k] = [item.model_dump() if hasattr(item, "model_dump") else item for item in v]
                elif hasattr(v, "model_dump"):
                    res[k] = v.model_dump()
                else:
                    res[k] = v
            return res
        def dict(self) -> Dict[str, Any]:
            return self.model_dump()

    def Field(default=None, default_factory=None, description=""):
        if default_factory is not None:
            return default_factory()
        return default

class InvoiceItem(BaseModel):
    description: str = Field(default="", description="Description of the product or service")
    hsn_sac_code: Optional[str] = Field(default="", description="HSN or SAC classification code if available")
    quantity: float = Field(default=1.0, description="Quantity of items")
    unit_price: float = Field(default=0.0, description="Unit price before tax")
    tax_rate_pct: float = Field(default=18.0, description="Tax rate percentage")
    line_total: float = Field(default=0.0, description="Total amount for this line item")

class ExtractedInvoice(BaseModel):
    invoice_number: str = Field(default="", description="Unique invoice/bill identifier")
    invoice_date: str = Field(default="", description="Date of the invoice")
    due_date: Optional[str] = Field(default=None, description="Due date for payment")
    vendor_name: str = Field(default="", description="Name of the seller / supplier")
    vendor_tax_id: str = Field(default="", description="Tax registration number (GSTIN, VAT, EIN)")
    customer_name: str = Field(default="", description="Name of the buyer / client")
    customer_tax_id: Optional[str] = Field(default="", description="Buyer's Tax ID / GSTIN")
    expense_category: str = Field(
        default="General Expense", 
        description="Expense category: IT Services, Office Supplies, Food & Dining, Travel, Machinery, Professional Fees, Luxury, Personal"
    )
    items: List[InvoiceItem] = Field(default_factory=list, description="List of line items")
    subtotal: float = Field(default=0.0, description="Total amount before tax")
    cgst: Optional[float] = Field(default=0.0, description="Central GST portion")
    sgst: Optional[float] = Field(default=0.0, description="State GST portion")
    igst: Optional[float] = Field(default=0.0, description="Integrated GST portion")
    total_tax: float = Field(default=0.0, description="Total tax amount")
    grand_total: float = Field(default=0.0, description="Final billed total amount payable")
    currency: str = Field(default="INR", description="Currency symbol or code (INR, USD, GBP, EUR)")

    def __init__(self, **kwargs):
        # Normalize items if passed as list of dicts
        raw_items = kwargs.get("items", [])
        clean_items = []
        for itm in raw_items:
            if isinstance(itm, dict):
                clean_items.append(InvoiceItem(**itm))
            else:
                clean_items.append(itm)
        kwargs["items"] = clean_items
        super().__init__(**kwargs)

class AuditFlag(BaseModel):
    category: str = Field(default="Audit", description="Arithmetic, Compliance, ITC Eligibility, or Vendor Verification")
    severity: str = Field(default="INFO", description="CRITICAL, WARNING, or INFO")
    issue: str = Field(default="", description="Brief title of the finding")
    details: str = Field(default="", description="Explanation of the discrepancy")
    recommendation: str = Field(default="", description="Actionable CA advice for rectification")

class AuditReport(BaseModel):
    invoice_number: str = Field(default="")
    vendor_name: str = Field(default="")
    is_arithmetic_valid: bool = Field(default=True)
    calculated_subtotal: float = Field(default=0.0)
    calculated_tax: float = Field(default=0.0)
    calculated_total: float = Field(default=0.0)
    math_difference: float = Field(default=0.0)
    is_tax_id_valid: bool = Field(default=True)
    itc_status: str = Field(default="ELIGIBLE")
    itc_reasoning: str = Field(default="")
    flags: List[AuditFlag] = Field(default_factory=list)
    overall_risk_score: str = Field(default="LOW")
    executive_summary: str = Field(default="")

    def __init__(self, **kwargs):
        raw_flags = kwargs.get("flags", [])
        clean_flags = []
        for flg in raw_flags:
            if isinstance(flg, dict):
                clean_flags.append(AuditFlag(**flg))
            else:
                clean_flags.append(flg)
        kwargs["flags"] = clean_flags
        super().__init__(**kwargs)

class ReconciliationMatch(BaseModel):
    invoice_number: str = Field(default="")
    vendor_name: str = Field(default="")
    invoice_amount: float = Field(default=0.0)
    matched_transaction_ref: Optional[str] = Field(default=None)
    transaction_date: Optional[str] = Field(default=None)
    amount_paid: float = Field(default=0.0)
    discrepancy: float = Field(default=0.0)
    status: str = Field(default="UNPAID")
    notes: str = Field(default="")
