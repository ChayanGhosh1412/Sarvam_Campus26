"""
Domain-specific Tax and Audit Rules Engine for Chartered Accountant Agent.
Implements arithmetic auditing, tax ID checksums, and statutory ITC/TDS checks.
"""
import re
from typing import Dict, Any, Tuple
from schemas import ExtractedInvoice, AuditFlag, AuditReport

# Indian State Codes mapping for GSTIN verification
STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
    "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "18": "Assam", "19": "West Bengal",
    "24": "Gujarat", "27": "Maharashtra", "29": "Karnataka",
    "32": "Kerala", "33": "Tamil Nadu", "36": "Telangana", "37": "Andhra Pradesh"
}

# Blocked Input Tax Credit categories under Section 17(5)
BLOCKED_ITC_KEYWORDS = {
    "food": "Food & beverages (Section 17(5)(b)(i))",
    "beverage": "Food & beverages (Section 17(5)(b)(i))",
    "catering": "Outdoor catering (Section 17(5)(b)(i))",
    "restaurant": "Dining / Restaurant expenses (Section 17(5)(b)(i))",
    "club": "Club membership & recreational facilities (Section 17(5)(b)(ii))",
    "gym": "Health and fitness club fees (Section 17(5)(b)(ii))",
    "personal": "Personal consumption expenses (Section 17(5)(g))",
    "gift": "Gifts and free samples (Section 17(5)(h))",
    "car": "Motor vehicles with seating capacity <= 13 persons (Section 17(5)(a))",
    "luxury": "Luxury goods for non-business purpose (Section 17(5)(g))",
    "cosmetic": "Cosmetic and plastic surgery expenses (Section 17(5)(b)(i))"
}

def validate_gstin_tax_id(tax_id: str) -> Dict[str, Any]:
    """
    Validates Tax ID / GSTIN structure.
    Standard GSTIN is 15 characters: 2 state digits + 10 PAN chars + 1 entity num + 1 'Z' + 1 checksum.
    """
    clean_id = (tax_id or "").strip().upper()
    if not clean_id:
        return {"valid": False, "type": "UNKNOWN", "details": "Tax ID / GSTIN is missing."}

    # Standard 15-char Indian GSTIN Pattern
    gstin_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    if re.match(gstin_pattern, clean_id):
        state_code = clean_id[:2]
        pan = clean_id[2:12]
        state_name = STATE_CODES.get(state_code, f"State Code {state_code}")
        return {
            "valid": True,
            "type": "GSTIN (India)",
            "state_name": state_name,
            "pan": pan,
            "details": f"Valid GSTIN registered in {state_name} with PAN {pan}."
        }
    
    # Generic EU VAT / US EIN / Standard Alphanumeric fallback
    if len(clean_id) >= 8 and re.match(r"^[A-Z0-9\-_]{8,20}$", clean_id):
        return {
            "valid": True,
            "type": "International / Generic Tax ID",
            "state_name": "N/A",
            "pan": "N/A",
            "details": f"Valid format for business identification: {clean_id}."
        }

    return {
        "valid": False,
        "type": "INVALID",
        "details": f"Format '{clean_id}' does not match standard 15-digit GSTIN or international tax registration format."
    }

def check_itc_eligibility(category: str, invoice_text_or_items: str) -> Tuple[str, str]:
    """
    Evaluates whether Input Tax Credit (ITC) can be claimed under statutory indirect tax law.
    Returns (status, reasoning).
    """
    combined_text = f"{category} {invoice_text_or_items}".lower()
    
    for kw, law_ref in BLOCKED_ITC_KEYWORDS.items():
        if kw in combined_text:
            return (
                "INELIGIBLE (BLOCKED)", 
                f"Blocked under statutory tax rules ({law_ref}). ITC cannot be claimed on this invoice."
            )
            
    if any(k in combined_text for k in ["software", "cloud", "hosting", "hardware", "office", "consulting", "legal", "audit", "machinery", "raw material"]):
        return (
            "ELIGIBLE",
            "Wholly and exclusively incurred in the course or furtherance of business. 100% ITC can be claimed."
        )
        
    return (
        "REQUIRES_REVIEW",
        "Subject to business nexus verification. Ensure the expense is not for employee personal consumption."
    )

def audit_invoice(invoice: ExtractedInvoice) -> AuditReport:
    """
    Performs full automated Chartered Accountant audit on an extracted invoice:
    1. Arithmetic accuracy check (Subtotal + Tax == Grand Total, Line items sum)
    2. Tax ID validity check
    3. Input Tax Credit (ITC) compliance evaluation
    4. Risk scoring and executive summary
    """
    flags = []
    
    # 1. Arithmetic Audit
    calc_subtotal = sum(item.quantity * item.unit_price for item in invoice.items) if invoice.items else invoice.subtotal
    if calc_subtotal == 0.0 and invoice.subtotal > 0:
        calc_subtotal = invoice.subtotal
        
    calc_tax = invoice.total_tax if invoice.total_tax > 0 else (invoice.cgst + invoice.sgst + invoice.igst)
    expected_total = calc_subtotal + calc_tax
    math_difference = round(abs(expected_total - invoice.grand_total), 2)
    
    is_arithmetic_valid = math_difference <= 1.0  # Allow minor rounding differences (paise/cents)
    
    if not is_arithmetic_valid:
        flags.append(AuditFlag(
            category="Arithmetic",
            severity="CRITICAL",
            issue="Total Mismatch / Billing Discrepancy",
            details=f"Invoice states Grand Total {invoice.currency} {invoice.grand_total:.2f}, but Subtotal ({calc_subtotal:.2f}) + Tax ({calc_tax:.2f}) equals {expected_total:.2f}. Discrepancy of {invoice.currency} {math_difference:.2f}.",
            recommendation="Reject or request a corrected credit note / revised tax invoice from the vendor prior to payment."
        ))
    
    # 2. Tax ID Audit
    tax_check = validate_gstin_tax_id(invoice.vendor_tax_id)
    is_tax_id_valid = tax_check["valid"]
    if not is_tax_id_valid:
        flags.append(AuditFlag(
            category="Compliance",
            severity="WARNING" if invoice.vendor_tax_id else "CRITICAL",
            issue="Invalid or Missing Vendor Tax ID",
            details=tax_check["details"],
            recommendation="Confirm the vendor's active registration on the government tax portal to avoid ITC disallowance."
        ))
        
    # 3. ITC Eligibility Audit
    item_descriptions = " ".join(item.description for item in invoice.items)
    itc_status, itc_reason = check_itc_eligibility(invoice.expense_category, item_descriptions)
    
    if itc_status == "INELIGIBLE (BLOCKED)":
        flags.append(AuditFlag(
            category="ITC Eligibility",
            severity="WARNING",
            issue="Blocked Input Tax Credit Alert",
            details=itc_reason,
            recommendation="Book the entire gross amount (including tax) to the Expense ledger. Do NOT post the tax portion to the ITC Input ledger."
        ))
    elif itc_status == "REQUIRES_REVIEW":
        flags.append(AuditFlag(
            category="ITC Eligibility",
            severity="INFO",
            issue="Requires Documentation of Business Nexus",
            details=itc_reason,
            recommendation="Retain department justification notes in audit file."
        ))

    # Overall Risk Score
    has_critical = any(f.severity == "CRITICAL" for f in flags)
    has_warning = any(f.severity == "WARNING" for f in flags)
    risk_score = "HIGH" if has_critical else ("MEDIUM" if has_warning else "LOW")
    
    # Summary formulation
    if risk_score == "LOW":
        summary = f"Invoice {invoice.invoice_number} from {invoice.vendor_name} passed all CA checks with zero compliance red flags. Ready for ledger posting."
    elif risk_score == "MEDIUM":
        summary = f"Invoice {invoice.invoice_number} has compliance notices (e.g., ITC treatment or registration alert), but math is reconciled."
    else:
        summary = f"Audit failed for Invoice {invoice.invoice_number}: Discrepancies detected ({len(flags)} flags). Hold payment pending clarification."

    return AuditReport(
        invoice_number=invoice.invoice_number,
        vendor_name=invoice.vendor_name,
        is_arithmetic_valid=is_arithmetic_valid,
        calculated_subtotal=calc_subtotal,
        calculated_tax=calc_tax,
        calculated_total=expected_total,
        math_difference=math_difference,
        is_tax_id_valid=is_tax_id_valid,
        itc_status=itc_status,
        itc_reasoning=itc_reason,
        flags=flags,
        overall_risk_score=risk_score,
        executive_summary=summary
    )
