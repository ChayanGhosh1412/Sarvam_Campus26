"""
Chartered Accountant (CA) AI Agent - Professional Workshop Dashboard
Powered by Lightweight Models (Gemini Flash, Ollama, Groq, Offline Sandbox)
"""
import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime

from schemas import ExtractedInvoice, InvoiceItem, AuditReport
from agent import CAAgent
from tools.reconciliation import reconcile_invoices_with_bank_statement
from tools.financial_ratios import compute_financial_ratios

# ---------------------------------------------------------
# Page Setup & Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="FinSage - AI Chartered Accountant",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Corporate FinTech CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.02em;
        margin-bottom: 4px;
    }
    
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 24px;
    }

    .badge-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .badge-success {
        background-color: #DCFCE7;
        color: #15803D;
        border: 1px solid #86EFAC;
    }

    .badge-warning {
        background-color: #FEF3C7;
        color: #B45309;
        border: 1px solid #FCD34D;
    }

    .badge-danger {
        background-color: #FEE2E2;
        color: #B91C1C;
        border: 1px solid #FCA5A5;
    }

    .invoice-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 16px;
    }

    .stat-box {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    
    .stat-label {
        font-size: 0.8rem;
        color: #64748B;
        text-transform: uppercase;
        font-weight: 600;
    }
    
    .stat-value {
        font-size: 1.35rem;
        font-weight: 700;
        color: #0F172A;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Sidebar Configuration
# ---------------------------------------------------------
st.sidebar.markdown("## ⚙️ Model Settings")
st.sidebar.caption("Configure your lightweight AI engine")

# Load environment variables if .env exists
env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_file_path):
    with open(env_file_path, "r") as ef:
        for line in ef:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k] = v

DEFAULT_KEY = os.environ.get("SARVAM_API_KEY", "")

provider = st.sidebar.selectbox(
    "Provider / Engine",
    options=["sarvam", "gemini_flash", "openai_compatible", "groq", "ollama", "offline"],
    format_func=lambda x: {
        "sarvam": "🇮🇳 Sarvam AI (sarvam-105b — India's Sovereign LLM)",
        "gemini_flash": "⚡ Google Gemini Flash (Vision + Sub-second)",
        "openai_compatible": "🌐 Custom / OpenAI-Compatible Proxy",
        "groq": "🚀 Groq API (Llama 3.1 8B Instant)",
        "ollama": "🦙 Local Ollama (Llama 3.2 3B / Qwen)",
        "offline": "🛡️ Offline Sandbox (Zero-API Rule Engine)"
    }[x],
    index=0
)

api_key = DEFAULT_KEY
model_name = ""
endpoint_url = "https://api.sarvam.ai/v1"

if provider == "sarvam":
    api_key = st.sidebar.text_input("Sarvam Subscription Key", value=DEFAULT_KEY, type="password")
    endpoint_url = st.sidebar.text_input("Endpoint Base URL", value="https://api.sarvam.ai/v1")
    model_name = st.sidebar.selectbox("Sarvam Model", ["sarvam-105b-conversations", "sarvam-105b"])
    
    if st.sidebar.button("🔌 Test Sarvam AI Connection"):
        with st.sidebar.spinner("Testing Sarvam AI..."):
            try:
                import requests
                r = requests.post(
                    f"{endpoint_url.rstrip('/')}/chat/completions",
                    headers={"api-subscription-key": api_key, "Content-Type": "application/json"},
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": "Namaste! Are you ready to assist with Indian CA audits? Reply in 1 brief sentence."}]
                    },
                    timeout=10
                )
                if r.status_code == 200:
                    reply_text = r.json()["choices"][0]["message"]["content"]
                    st.sidebar.success("✅ Sarvam AI Connected!")
                    st.sidebar.caption(f"💬 *\"{reply_text}\"*")
                else:
                    st.sidebar.warning(f"Sarvam AI Error ({r.status_code}): {r.text[:120]}")
            except Exception as ex:
                st.sidebar.error(f"Error: {ex}")

elif provider == "openai_compatible":
    api_key = st.sidebar.text_input("API Key", value=DEFAULT_KEY, type="password")
    endpoint_url = st.sidebar.text_input("Endpoint Base URL", value="https://api.openai.com/v1", help="Or custom proxy URL e.g. http://localhost:8000/v1")
    model_name = st.sidebar.text_input("Model Name", value="gpt-4o-mini", help="Or meta-llama/llama-3.2-3b-instruct, mistral-7b, etc.")
    
    if st.sidebar.button("🔌 Test API Connection"):
        with st.sidebar.spinner("Testing connection..."):
            try:
                import requests
                r = requests.get(f"{endpoint_url.rstrip('/')}/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=6)
                if r.status_code == 200:
                    st.sidebar.success("✅ Connection Successful!")
                else:
                    st.sidebar.warning(f"Response ({r.status_code}): {r.text[:120]}")
            except Exception as ex:
                st.sidebar.error(f"Error: {ex}")

elif provider == "gemini_flash":
    api_key = st.sidebar.text_input(
        "Gemini API Key", 
        value=os.environ.get("GEMINI_API_KEY", DEFAULT_KEY), 
        type="password",
        placeholder="AIzaSy...",
        help="Free key from aistudio.google.com"
    )
    model_name = st.sidebar.selectbox("Model", ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash"])
    if st.sidebar.button("🔌 Test Gemini Connection"):
        with st.sidebar.spinner("Testing connection..."):
            try:
                import requests
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}",
                    json={"contents": [{"parts": [{"text": "hi"}]}]},
                    timeout=6
                )
                if r.status_code == 200:
                    st.sidebar.success("✅ Gemini Connected!")
                else:
                    st.sidebar.warning(f"Gemini error ({r.status_code}): {r.text[:120]}")
            except Exception as ex:
                st.sidebar.error(f"Error: {ex}")

elif provider == "groq":
    api_key = st.sidebar.text_input("Groq API Key", value=os.environ.get("GROQ_API_KEY", DEFAULT_KEY), type="password")
    model_name = st.sidebar.selectbox("Model", ["llama-3.1-8b-instant", "llama-3.2-3b-preview"])
    if st.sidebar.button("🔌 Test Groq Connection"):
        with st.sidebar.spinner("Testing Groq..."):
            try:
                import requests
                r = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=6)
                if r.status_code == 200:
                    st.sidebar.success("✅ Groq Connected!")
                else:
                    st.sidebar.warning(f"Groq ({r.status_code}): {r.text[:120]}")
            except Exception as ex:
                st.sidebar.error(f"Error: {ex}")

elif provider == "ollama":
    endpoint_url = st.sidebar.text_input("Ollama Host", value="http://localhost:11434")
    model_name = st.sidebar.text_input("Model Tag", value="llama3.2:3b")

agent = CAAgent(
    provider=provider,
    api_key=api_key,
    model_name=model_name,
    endpoint_url=endpoint_url
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎓 Workshop Facilitator")
st.sidebar.info(
    "💡 **Workshop Tip:** Your API key is loaded! If using a custom proxy/endpoint, adjust the 'Endpoint Base URL'. You can also switch to 'Offline Sandbox' anytime to test rule engines locally without external calls."
)

# ---------------------------------------------------------
# Load Sample Files
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_data")
sample_invoices_path = os.path.join(SAMPLE_DIR, "sample_invoices.json")
sample_bank_path = os.path.join(SAMPLE_DIR, "sample_bank_statement.csv")
sample_fin_path = os.path.join(SAMPLE_DIR, "sample_financials.json")

with open(sample_invoices_path, "r") as f:
    sample_invoices_data = json.load(f)

# ---------------------------------------------------------
# Header Section
# ---------------------------------------------------------
st.markdown('<div class="main-title">💼 FinSage — Chartered Accountant AI Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Autonomous Tax Auditing, Document Extraction, Bank Reconciliation & Advisory with Lightweight Models</div>', unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📑 1. Invoice Audit & ITC",
    "⚖️ 2. Bank Reconciliation",
    "📊 3. Financial Ratio Diagnostics",
    "💬 4. Conversational Tax Advisor",
    "📖 5. Workshop Architecture"
])

# =========================================================
# TAB 1: INVOICE AUDIT & ITC
# =========================================================
with tab1:
    st.markdown("### 📑 Invoice Ingestion & Statutory Compliance Audit")
    st.caption("Extract structured data from supplier bills, then automatically audit arithmetic accuracy, GSTIN state code, and Section 17(5) Input Tax Credit eligibility.")

    col_in, col_audit = st.columns([1, 1], gap="medium")

    current_invoice: ExtractedInvoice = None

    with col_in:
        input_mode = st.radio("Input Source", ["Workshop Presets (Instant Demo)", "Upload File (PNG, JPG, PDF, TXT)", "Paste Text"], horizontal=True)

        if input_mode == "Workshop Presets (Instant Demo)":
            sample_choice = st.selectbox(
                "Select a Preset Test Invoice:",
                [
                    "Sample A: TechNova Cloud Infrastructure (Clean & 100% ITC Eligible)",
                    "Sample B: Swift Freight & Logistics (CRITICAL Math Mismatch Error)",
                    "Sample C: Grand Palace Luxury Resort (BLOCKED ITC under Section 17(5))"
                ]
            )
            idx = 0 if "Sample A" in sample_choice else (1 if "Sample B" in sample_choice else 2)
            current_invoice = ExtractedInvoice(**sample_invoices_data[idx])

        elif input_mode == "Upload File (PNG, JPG, PDF, TXT)":
            uploaded_file = st.file_uploader("Upload Invoice Bill", type=["png", "jpg", "jpeg", "pdf", "txt"])
            if uploaded_file is not None:
                if st.button("🚀 Process & Audit Invoice", type="primary"):
                    with st.spinner("Extracting with Lightweight Agent..."):
                        file_bytes = uploaded_file.read()
                        mime = uploaded_file.type
                        if "text" in mime or uploaded_file.name.endswith(".txt"):
                            current_invoice = agent.extract_invoice_data(raw_text=file_bytes.decode("utf-8", errors="ignore"))
                        else:
                            current_invoice = agent.extract_invoice_data(file_bytes=file_bytes, mime_type=mime)
        else:
            raw_input_text = st.text_area("Paste Raw Invoice Text", height=180, placeholder="Tax Invoice\nVendor: TechNova Cloud\nGSTIN: 27AABCT1234D1Z5\nSubtotal: 50,000\nTotal: 59,000")
            if st.button("🚀 Process & Audit Text", type="primary"):
                if raw_input_text.strip():
                    with st.spinner("Extracting with Lightweight Agent..."):
                        current_invoice = agent.extract_invoice_data(raw_text=raw_input_text)
                else:
                    st.warning("Please paste invoice text first.")

        # Render Invoice Visual Mockup Card
        if current_invoice:
            st.markdown("#### 📄 Document Preview")
            items_html = "".join([
                f"<tr><td>{item.description}</td><td>{item.quantity}</td><td>₹ {item.unit_price:,.2f}</td><td>{item.tax_rate_pct}%</td><td><b>₹ {item.line_total:,.2f}</b></td></tr>"
                for item in current_invoice.items
            ])
            st.markdown(f"""
            <div class="invoice-card">
                <div style="display:flex; justify-content:space-between; border-bottom:1px solid #CBD5E1; padding-bottom:10px;">
                    <div>
                        <h4 style="margin:0; color:#0F172A;">{current_invoice.vendor_name}</h4>
                        <span style="font-size:0.85rem; color:#64748B;">Tax ID / GSTIN: <b>{current_invoice.vendor_tax_id or 'NOT PROVIDED'}</b></span>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:0.85rem; color:#64748B;">Invoice: <b>{current_invoice.invoice_number}</b></span><br>
                        <span style="font-size:0.85rem; color:#64748B;">Date: {current_invoice.invoice_date}</span>
                    </div>
                </div>
                <div style="margin:12px 0;">
                    <span style="font-size:0.85rem; color:#64748B;">Billed To: <b>{current_invoice.customer_name}</b> | Category: <i>{current_invoice.expense_category}</i></span>
                </div>
                <table style="width:100%; font-size:0.85rem; border-collapse:collapse; margin-top:8px;">
                    <tr style="border-bottom:1px solid #E2E8F0; text-align:left; color:#64748B;">
                        <th>Description</th><th>Qty</th><th>Rate</th><th>Tax</th><th>Amount</th>
                    </tr>
                    {items_html}
                </table>
                <div style="margin-top:14px; text-align:right; border-top:1px solid #CBD5E1; padding-top:8px;">
                    <span style="font-size:0.85rem; color:#64748B;">Subtotal: ₹ {current_invoice.subtotal:,.2f} | Tax: ₹ {current_invoice.total_tax:,.2f}</span><br>
                    <span style="font-size:1.15rem; font-weight:700; color:#0F172A;">Billed Grand Total: {current_invoice.currency} {current_invoice.grand_total:,.2f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_audit:
        if current_invoice:
            audit_report = agent.run_full_audit(current_invoice)

            # Risk Header Pill
            if audit_report.overall_risk_score == "LOW":
                badge_html = '<span class="badge-pill badge-success">✅ LOW RISK (AUDIT PASSED)</span>'
            elif audit_report.overall_risk_score == "MEDIUM":
                badge_html = '<span class="badge-pill badge-warning">⚠️ MEDIUM RISK (COMPLIANCE NOTICE)</span>'
            else:
                badge_html = '<span class="badge-pill badge-danger">🚨 HIGH RISK (DISCREPANCY DETECTED)</span>'

            st.markdown(f"#### 🛡️ CA Audit Finding: {badge_html}", unsafe_allow_html=True)
            st.info(audit_report.executive_summary)

            # Metric Cards
            s1, s2, s3 = st.columns(3)
            with s1:
                st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label">Billed Amount</div>
                    <div class="stat-value">₹ {current_invoice.grand_total:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            with s2:
                diff_label = f"Diff: ₹ {audit_report.math_difference:,.2f}" if audit_report.math_difference > 1.0 else "Reconciled"
                diff_color = "#DC2626" if audit_report.math_difference > 1.0 else "#16A34A"
                st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label">Verified Total</div>
                    <div class="stat-value" style="color:{diff_color}">₹ {audit_report.calculated_total:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            with s3:
                itc_color = "#15803D" if "ELIGIBLE" in audit_report.itc_status and "INELIGIBLE" not in audit_report.itc_status else "#B91C1C"
                st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label">ITC Status</div>
                    <div class="stat-value" style="font-size:1.05rem; color:{itc_color}">{audit_report.itc_status}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("#### 🔍 Statutory & Arithmetic Flags")
            if not audit_report.flags:
                st.success("🎉 **Zero Compliance Discrepancies:** All mathematical calculations balance, vendor tax ID is in valid format, and expenditure is 100% allowable.")
            else:
                for flg in audit_report.flags:
                    sev_class = "badge-danger" if flg.severity == "CRITICAL" else ("badge-warning" if flg.severity == "WARNING" else "badge-success")
                    st.markdown(f"""
                    <div style="background:#FFF; border:1px solid #E2E8F0; border-left:4px solid {'#EF4444' if flg.severity=='CRITICAL' else '#F59E0B'}; border-radius:6px; padding:12px; margin-bottom:10px;">
                        <span class="badge-pill {sev_class}" style="font-size:0.75rem;">{flg.severity} - {flg.category}</span>
                        <h5 style="margin:6px 0 2px 0; color:#0F172A;">{flg.issue}</h5>
                        <p style="margin:0 0 6px 0; font-size:0.9rem; color:#475569;">{flg.details}</p>
                        <div style="font-size:0.85rem; color:#0369A1; background:#F0F9FF; padding:6px 10px; border-radius:4px;">
                            <b>CA Advisory:</b> {flg.recommendation}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # Download Audit Certificate
            audit_json_str = json.dumps(audit_report.model_dump(), indent=2)
            st.download_button(
                "📥 Download CA Audit Report (JSON)",
                data=audit_json_str,
                file_name=f"audit_report_{current_invoice.invoice_number}.json",
                mime="application/json"
            )

# =========================================================
# TAB 2: BANK RECONCILIATION
# =========================================================
with tab2:
    st.markdown("### ⚖️ Automated Bank Statement & Ledger Reconciliation")
    st.caption("Reconcile multiple vendor invoices against bank account transaction feeds with automated TDS withholding detection.")

    b_col1, b_col2 = st.columns([1, 2], gap="large")

    with b_col1:
        st.markdown("#### 1. Ingestion Data")
        use_preset_bank = st.checkbox("Use Workshop Bank Statement Feed", value=True)
        
        if use_preset_bank:
            df_bank = pd.read_csv(sample_bank_path)
            invoices_recon = [ExtractedInvoice(**x) for x in sample_invoices_data]
            st.success(f"Loaded {len(invoices_recon)} vendor invoices & {len(df_bank)} bank transactions.")
        else:
            bank_upload = st.file_uploader("Upload Bank Statement (CSV)", type=["csv"])
            if bank_upload:
                df_bank = pd.read_csv(bank_upload)
            else:
                df_bank = None
            invoices_recon = [ExtractedInvoice(**x) for x in sample_invoices_data]

    with b_col2:
        if df_bank is not None:
            st.markdown("#### 2. Bank Transaction Feed Preview")
            st.dataframe(df_bank, height=200, use_container_width=True)

    if df_bank is not None:
        st.markdown("---")
        matches, metrics = reconcile_invoices_with_bank_statement(invoices_recon, df_bank)

        # Overview Metrics Cards
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Billed", f"₹ {metrics['total_billed']:,.2f}")
        m2.metric("Total Paid in Bank", f"₹ {metrics['total_paid']:,.2f}")
        m3.metric("Outstanding Balance", f"₹ {metrics['total_outstanding']:,.2f}", delta=f"-{metrics['unpaid_count']} unpaid", delta_color="inverse")
        m4.metric("Reconciliation Rate", f"{metrics['reconciliation_rate_pct']}%")

        st.markdown("#### 3. Invoice-to-Bank Reconciliation Ledger")
        
        filter_status = st.selectbox("Filter Status", ["All", "MATCHED_PAID", "UNPAID", "UNDERPAID"])

        recon_rows = []
        for m in matches:
            if filter_status != "All" and m.status != filter_status:
                continue
            status_badge = "🟢 MATCHED" if "MATCHED" in m.status else ("🔴 UNPAID" if "UNPAID" in m.status else "🟠 " + m.status)
            recon_rows.append({
                "Invoice #": m.invoice_number,
                "Vendor": m.vendor_name,
                "Invoice Amount": f"₹ {m.invoice_amount:,.2f}",
                "Paid Amount": f"₹ {m.amount_paid:,.2f}",
                "Status": status_badge,
                "Bank Ref / UTR": m.matched_transaction_ref or "—",
                "Payment Date": m.transaction_date or "—",
                "Reconciliation Notes": m.notes
            })
        
        df_recon = pd.DataFrame(recon_rows)
        st.dataframe(df_recon, use_container_width=True)

        # Export CSV
        csv_recon = df_recon.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Export Reconciliation Ledger (CSV)",
            data=csv_recon,
            file_name="bank_reconciliation_ledger.csv",
            mime="text/csv"
        )

# =========================================================
# TAB 3: FINANCIAL RATIOS
# =========================================================
with tab3:
    st.markdown("### 📊 Financial Statement Health & Diagnostic Ratios")
    st.caption("Calculate critical corporate solvency, working capital liquidity, and operating margin ratios with automated CA commentary.")

    with open(sample_fin_path, "r") as f:
        sample_fin_data = json.load(f)

    st.button("🔄 Reset to Workshop Benchmark Figures")

    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown("#### 📈 Income Statement")
        rev = st.number_input("Annual Revenue / Turnover (₹)", value=float(sample_fin_data["financials"]["revenue"]), step=500000.0)
        cogs = st.number_input("Cost of Goods Sold (COGS) (₹)", value=float(sample_fin_data["financials"]["cogs"]), step=200000.0)
        ebit = st.number_input("Operating Profit (EBIT) (₹)", value=float(sample_fin_data["financials"]["ebit"]), step=100000.0)
        interest = st.number_input("Finance / Interest Expense (₹)", value=float(sample_fin_data["financials"]["interest_expense"]), step=50000.0)
        net_profit = st.number_input("Net Profit (PAT) (₹)", value=float(sample_fin_data["financials"]["net_profit"]), step=50000.0)

    with f2:
        st.markdown("#### 💧 Working Capital & Assets")
        ca = st.number_input("Current Assets (₹)", value=float(sample_fin_data["financials"]["current_assets"]), step=200000.0)
        inventory = st.number_input("Inventory / Stock (₹)", value=float(sample_fin_data["financials"]["inventory"]), step=100000.0)
        cash = st.number_input("Cash & Bank Balances (₹)", value=float(sample_fin_data["financials"]["cash"]), step=50000.0)
        cl = st.number_input("Current Liabilities (₹)", value=float(sample_fin_data["financials"]["current_liabilities"]), step=200000.0)

    with f3:
        st.markdown("#### 🏛️ Capital Structure")
        debt = st.number_input("Total Debt / Borrowings (₹)", value=float(sample_fin_data["financials"]["total_debt"]), step=200000.0)
        equity = st.number_input("Net Worth / Total Equity (₹)", value=float(sample_fin_data["financials"]["total_equity"]), step=200000.0)

    fin_inputs = {
        "revenue": rev, "cogs": cogs, "ebit": ebit, "interest_expense": interest, "net_profit": net_profit,
        "current_assets": ca, "inventory": inventory, "cash": cash, "current_liabilities": cl,
        "total_debt": debt, "total_equity": equity
    }

    ratio_results = compute_financial_ratios(fin_inputs)
    r = ratio_results["ratios"]

    st.markdown("---")
    st.markdown("#### 🩺 Financial Health Scorecard")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Current Ratio", f"{r.get('current_ratio', 0.0)}x", help="Standard Bank Benchmark >= 1.33x")
    k2.metric("Quick Ratio", f"{r.get('quick_ratio', 0.0)}x", help="Standard Benchmark >= 1.0x")
    k3.metric("Debt-to-Equity", f"{r.get('debt_to_equity', 0.0)}", help="Safe Limit < 1.5x")
    k4.metric("Interest Coverage", f"{r.get('interest_coverage', 0.0)}x", help="Healthy Coverage > 2.5x")
    k5.metric("Net Margin", f"{r.get('net_profit_margin_pct', 0.0)}%")

    st.markdown("#### 📝 CA Diagnostic Commentary")
    for diag in ratio_results["diagnostics"]:
        diag_icon = "🟢" if diag["severity"] == "GOOD" else ("🟠" if diag["severity"] == "WARNING" else "🔴")
        st.markdown(f"- {diag_icon} **{diag['type']}:** {diag['text']}")

# =========================================================
# TAB 4: CONVERSATIONAL TAX ADVISOR
# =========================================================
with tab4:
    st.markdown("### 💬 Conversational Statutory Tax Advisor")
    st.caption("Consult your AI Chartered Accountant on TDS rates, GST circulars, depreciation schedules, and corporate tax compliance.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Hello! I am your AI Chartered Accountant partner. Ask me about TDS sections, GST Input Tax Credit rules, statutory depreciation, or audit provisions."}
        ]

    # Sample Quick Prompts
    st.markdown("**💡 Quick Workshop Demonstration Queries:**")
    prompt_cols = st.columns(3)
    with prompt_cols[0]:
        if st.button("📌 TDS Rates: 194C vs 194J", use_container_width=True):
            st.session_state.chat_history.append({"role": "user", "content": "What is the TDS rate under Section 194C vs 194J?"})
            st.session_state.chat_history.append({"role": "assistant", "content": agent.ask_tax_advisor("What is the TDS rate under Section 194C vs 194J?")})
    with prompt_cols[1]:
        if st.button("🚫 Blocked ITC on Dining / Cars", use_container_width=True):
            st.session_state.chat_history.append({"role": "user", "content": "Can a business claim input tax credit (ITC) on corporate dining and vehicle purchases?"})
            st.session_state.chat_history.append({"role": "assistant", "content": agent.ask_tax_advisor("Can a business claim input tax credit (ITC) on corporate dining and vehicle purchases?")})
    with prompt_cols[2]:
        if st.button("💻 Laptop Depreciation Rates", use_container_width=True):
            st.session_state.chat_history.append({"role": "user", "content": "What is the allowable statutory depreciation rate on office computers and laptops?"})
            st.session_state.chat_history.append({"role": "assistant", "content": agent.ask_tax_advisor("What is the allowable statutory depreciation rate on office computers and laptops?")})

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_chat = st.chat_input("Ask your CA partner a question (e.g. 'What is the threshold for Section 194Q?')...")
    if user_chat:
        st.session_state.chat_history.append({"role": "user", "content": user_chat})
        with st.chat_message("user"):
            st.markdown(user_chat)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing tax statutes..."):
                reply = agent.ask_tax_advisor(user_chat)
                st.markdown(reply)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})

# =========================================================
# TAB 5: WORKSHOP ARCHITECTURE
# =========================================================
with tab5:
    st.markdown("### 📖 Workshop Curriculum & Code Architecture")
    st.markdown("""
    #### Why this architecture is ideal for teaching Agentic Systems:
    1. **Never Let LLMs Do Math Directly:**
       - LLMs are probabilistic language generators, not calculators.
       - **Design Pattern:** The LLM is used strictly for **multimodal extraction into strict JSON schemas**. Deterministic calculations (subtotal + tax = total, TDS 10%, GSTIN state parsing) are delegated to Python engines (`tools/tax_rules.py`).
    2. **Lightweight Model Compatibility:**
       - Runs on **Gemini 1.5/2.0 Flash** (multimodal, fast, low cost) or **Local Ollama** (Llama 3.2 3B).
       - Zero-API **Offline Sandbox** mode guarantees no participant is held up by credential issues.
    3. **Hands-on Student Exercise Ideas:**
       - **Exercise 1:** Add a new audit flag in `tools/tax_rules.py` to mandate PAN collection for transactions exceeding ₹2,00,000 under Rule 114B.
       - **Exercise 2:** Extend `tools/reconciliation.py` to identify duplicate invoices based on identical vendor name and amount within a 30-day window.
    """)
