"""
Bank Statement and Ledger Reconciliation Engine for CA Agent.
Performs 2-way/3-way matching between Invoices and Bank Transactions.
"""
import re
from typing import List, Dict, Any, Tuple
import pandas as pd
from schemas import ExtractedInvoice, ReconciliationMatch

def reconcile_invoices_with_bank_statement(
    invoices: List[ExtractedInvoice],
    df_bank: pd.DataFrame
) -> Tuple[List[ReconciliationMatch], Dict[str, Any]]:
    """
    Reconciles a list of extracted invoices against a bank statement dataframe.
    Bank statement can have variations of columns: Date, Description, Reference, Debit/Withdrawal.
    """
    results: List[ReconciliationMatch] = []
    
    # Normalize column names in bank statement
    col_map = {}
    for col in df_bank.columns:
        c_lower = str(col).lower().strip()
        if "date" in c_lower:
            col_map["date"] = col
        elif any(k in c_lower for k in ["desc", "narration", "particular", "detail"]):
            col_map["desc"] = col
        elif any(k in c_lower for k in ["ref", "utr", "chq", "cheque", "txn"]):
            col_map["ref"] = col
        elif any(k in c_lower for k in ["debit", "withdrawal", "dr", "paid", "amount_out"]):
            col_map["debit"] = col
        elif any(k in c_lower for k in ["credit", "deposit", "cr", "received"]):
            col_map["credit"] = col
            
    # Clean numeric columns in bank statement
    debit_col = col_map.get("debit")
    desc_col = col_map.get("desc", df_bank.columns[0])
    date_col = col_map.get("date", df_bank.columns[0])
    ref_col = col_map.get("ref")

    bank_txns = []
    for idx, row in df_bank.iterrows():
        try:
            val = row[debit_col] if debit_col else 0.0
            if pd.isna(val) or val == "":
                amt = 0.0
            else:
                amt = float(str(val).replace(",", "").replace("₹", "").replace("$", "").strip())
        except Exception:
            amt = 0.0
            
        desc = str(row[desc_col]) if desc_col in row else ""
        date_str = str(row[date_col]) if date_col in row else ""
        ref_str = str(row[ref_col]) if ref_col and ref_col in row else f"TXN-{idx+1001}"
        
        bank_txns.append({
            "index": idx,
            "date": date_str,
            "desc": desc,
            "ref": ref_str,
            "debit": amt,
            "used": False
        })

    total_billed = 0.0
    total_paid = 0.0
    matched_count = 0
    unpaid_count = 0

    for inv in invoices:
        total_billed += inv.grand_total
        inv_no_clean = re.sub(r"[^A-Za-z0-9]", "", inv.invoice_number.lower())
        vendor_clean = inv.vendor_name.lower()
        
        matched_txn = None
        
        # Pass 1: Match by Invoice Number and exact/near amount
        for txn in bank_txns:
            if txn["used"] or txn["debit"] <= 0:
                continue
            txn_desc_clean = re.sub(r"[^A-Za-z0-9]", "", txn["desc"].lower())
            
            amount_diff = abs(txn["debit"] - inv.grand_total)
            has_inv_ref = inv_no_clean and (inv_no_clean in txn_desc_clean)
            
            # TDS allowance: often 1%, 2%, or 10% is deducted at source
            tds_10 = abs(txn["debit"] - (inv.grand_total * 0.90))
            tds_2 = abs(txn["debit"] - (inv.grand_total * 0.98))
            
            if has_inv_ref and (amount_diff < 1.0 or tds_10 < 1.0 or tds_2 < 1.0):
                matched_txn = txn
                break

        # Pass 2: Match by exact amount + vendor name in narrative
        if not matched_txn:
            for txn in bank_txns:
                if txn["used"] or txn["debit"] <= 0:
                    continue
                amount_diff = abs(txn["debit"] - inv.grand_total)
                vendor_matched = any(part in txn["desc"].lower() for part in vendor_clean.split() if len(part) > 3)
                
                if amount_diff < 1.0 and (vendor_matched or len(invoices) == 1):
                    matched_txn = txn
                    break

        # Pass 3: Match solely by exact amount if unambiguous
        if not matched_txn:
            candidates = [t for t in bank_txns if not t["used"] and abs(t["debit"] - inv.grand_total) < 1.0]
            if len(candidates) == 1:
                matched_txn = candidates[0]

        if matched_txn:
            matched_txn["used"] = True
            diff = round(inv.grand_total - matched_txn["debit"], 2)
            
            if abs(diff) < 1.0:
                status = "MATCHED_PAID"
                notes = f"Payment verified via bank ref {matched_txn['ref']} on {matched_txn['date']}."
                total_paid += matched_txn["debit"]
                matched_count += 1
            elif diff > 0 and (abs(diff - (inv.grand_total * 0.10)) < 2.0 or abs(diff - (inv.grand_total * 0.02)) < 2.0):
                status = "MATCHED_PAID"
                notes = f"Payment reconciled with TDS withholding ({inv.currency} {diff:.2f} deducted under Sec 194C/J)."
                total_paid += inv.grand_total
                matched_count += 1
            elif diff > 0:
                status = "UNDERPAID"
                notes = f"Partial payment received: {inv.currency} {matched_txn['debit']:.2f}. Balance outstanding: {inv.currency} {diff:.2f}."
                total_paid += matched_txn["debit"]
            else:
                status = "OVERPAID"
                notes = f"Overpayment detected: {inv.currency} {matched_txn['debit']:.2f} paid against {inv.currency} {inv.grand_total:.2f}."
                total_paid += matched_txn["debit"]

            results.append(ReconciliationMatch(
                invoice_number=inv.invoice_number,
                vendor_name=inv.vendor_name,
                invoice_amount=inv.grand_total,
                matched_transaction_ref=matched_txn["ref"],
                transaction_date=matched_txn["date"],
                amount_paid=matched_txn["debit"],
                discrepancy=diff,
                status=status,
                notes=notes
            ))
        else:
            unpaid_count += 1
            results.append(ReconciliationMatch(
                invoice_number=inv.invoice_number,
                vendor_name=inv.vendor_name,
                invoice_amount=inv.grand_total,
                matched_transaction_ref=None,
                transaction_date=None,
                amount_paid=0.0,
                discrepancy=inv.grand_total,
                status="UNPAID",
                notes="No matching bank debit transaction identified in current statement period."
            ))

    metrics = {
        "total_invoices": len(invoices),
        "total_billed": round(total_billed, 2),
        "total_paid": round(total_paid, 2),
        "total_outstanding": round(total_billed - total_paid, 2),
        "matched_count": matched_count,
        "unpaid_count": unpaid_count,
        "reconciliation_rate_pct": round((matched_count / len(invoices) * 100) if invoices else 0.0, 1)
    }

    return results, metrics
