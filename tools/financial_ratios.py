"""
Financial Ratio and Health Diagnostic Engine for CA Agent.
Computes Liquidity, Solvency, and Profitability ratios with CA advisory commentary.
"""
from typing import Dict, Any

def compute_financial_ratios(data: Dict[str, float]) -> Dict[str, Any]:
    """
    Computes key financial health indicators from balance sheet and income statement items.
    """
    revenue = float(data.get("revenue", 0.0))
    cogs = float(data.get("cogs", 0.0))
    net_profit = float(data.get("net_profit", 0.0))
    ebit = float(data.get("ebit", 0.0))
    interest_expense = float(data.get("interest_expense", 0.0))
    
    current_assets = float(data.get("current_assets", 0.0))
    inventory = float(data.get("inventory", 0.0))
    cash = float(data.get("cash", 0.0))
    current_liabilities = float(data.get("current_liabilities", 0.0))
    
    total_debt = float(data.get("total_debt", 0.0))
    total_equity = float(data.get("total_equity", 0.0))
    total_assets = float(data.get("total_assets", current_assets + total_equity))

    ratios = {}
    diagnostics = []

    # 1. Liquidity Ratios
    if current_liabilities > 0:
        current_ratio = round(current_assets / current_liabilities, 2)
        quick_ratio = round((current_assets - inventory) / current_liabilities, 2)
        cash_ratio = round(cash / current_liabilities, 2)
        
        ratios["current_ratio"] = current_ratio
        ratios["quick_ratio"] = quick_ratio
        ratios["cash_ratio"] = cash_ratio

        if current_ratio < 1.0:
            diagnostics.append({
                "type": "Liquidity Alert",
                "severity": "CRITICAL",
                "text": f"Current Ratio ({current_ratio}) is below 1.0. The firm faces immediate working capital deficit and potential liquidity distress."
            })
        elif current_ratio < 1.33:
            diagnostics.append({
                "type": "Liquidity Notice",
                "severity": "WARNING",
                "text": f"Current Ratio ({current_ratio}) is tight (Standard bank benchmark is 1.33). Consider lengthening payable terms."
            })
        else:
            diagnostics.append({
                "type": "Liquidity",
                "severity": "GOOD",
                "text": f"Current Ratio ({current_ratio}) exhibits healthy short-term solvency buffer."
            })
    else:
        ratios["current_ratio"] = 0.0
        ratios["quick_ratio"] = 0.0
        ratios["cash_ratio"] = 0.0

    # 2. Leverage & Solvency
    if total_equity > 0:
        de_ratio = round(total_debt / total_equity, 2)
        ratios["debt_to_equity"] = de_ratio
        
        if de_ratio > 2.0:
            diagnostics.append({
                "type": "Leverage Warning",
                "severity": "WARNING",
                "text": f"Debt-to-Equity is {de_ratio}. High financial leverage amplifies vulnerability during cyclical downturns."
            })
        else:
            diagnostics.append({
                "type": "Solvency",
                "severity": "GOOD",
                "text": f"Debt-to-Equity ({de_ratio}) indicates balanced capital structure and moderate financial risk."
            })
    else:
        ratios["debt_to_equity"] = 0.0

    if interest_expense > 0:
        icr = round(ebit / interest_expense, 2)
        ratios["interest_coverage"] = icr
        if icr < 2.0:
            diagnostics.append({
                "type": "Debt Servicing",
                "severity": "CRITICAL",
                "text": f"Interest Coverage Ratio is low ({icr}x). Operating profit barely covers finance charges."
            })
        else:
            diagnostics.append({
                "type": "Debt Servicing",
                "severity": "GOOD",
                "text": f"Interest Coverage Ratio ({icr}x) comfortably satisfies bank debt-servicing covenants."
            })
    else:
        ratios["interest_coverage"] = 999.0

    # 3. Profitability Ratios
    if revenue > 0:
        gross_margin = round(((revenue - cogs) / revenue) * 100, 2)
        net_margin = round((net_profit / revenue) * 100, 2)
        ratios["gross_profit_margin_pct"] = gross_margin
        ratios["net_profit_margin_pct"] = net_margin
    else:
        ratios["gross_profit_margin_pct"] = 0.0
        ratios["net_profit_margin_pct"] = 0.0

    if total_equity > 0:
        roe = round((net_profit / total_equity) * 100, 2)
        ratios["roe_pct"] = roe
    else:
        ratios["roe_pct"] = 0.0

    return {
        "ratios": ratios,
        "diagnostics": diagnostics,
        "summary": "Financial diagnostic complete. Review working capital adequacy and debt covenants."
    }
