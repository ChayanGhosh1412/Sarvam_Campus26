# 💼 AI Chartered Accountant (CA) Agent — Workshop Edition

An intelligent, production-ready Chartered Accountant agent designed specifically for **hands-on workshops**, powered by **Sarvam AI (India's Sovereign `sarvam-105b` Model)** alongside lightweight models (Google Gemini Flash, Ollama Llama 3.2 3B, Groq, and an Offline Sandbox mode).

---

## 🌟 What This Agent Does

1. **🇮🇳 Powered by Sarvam AI (`sarvam-105b-conversations`):**
   - Natively trained with deep understanding of Indian taxation laws, GST circulars, TDS sections (Income Tax Act), and bilingual financial terminology.

1. **📑 Invoice & Receipt Intelligence:**
   - Extracts structured invoice data (Vendor, GSTIN/Tax ID, Items, Taxes, Grand Total) from images, PDFs, or raw text.
   - Detects billing errors and arithmetic mismatches (subtotal + tax $\neq$ total).
   - Validates Tax IDs / GSTIN structure and extracts state registration.
   - Audits **Input Tax Credit (ITC)** under statutory rules (flags Section 17(5) blocked credits like dining, personal luxury, etc.).

2. **⚖️ Automated Bank Statement Reconciliation:**
   - Ingests bank statement transaction feeds (CSV).
   - Reconciles paid vs. unpaid invoices.
   - Handles TDS withholding deductions (e.g., 10% under Sec 194J or 2% under Sec 194C) without false mismatch alarms.

3. **📊 Financial Health & Ratio Diagnostics:**
   - Computes Current, Quick, Cash, Debt-to-Equity, Interest Coverage, and Net Profit Margin ratios.
   - Generates automated CA diagnostic audit remarks on working capital risk.

4. **💬 Statutory Tax Advisor (RAG & Compliance Chat):**
   - Answers business tax queries with statutory sections (TDS, GST, Depreciation schedules).

5. **🛡️ 100% Workshop Ready (Offline Sandbox Included):**
   - No attendee gets left behind! If someone doesn't have an API key or internet, they can toggle **Offline Sandbox** to run all audits and reconciliations with built-in presets.

---

## 🚀 Quickstart

### 1. Navigate to the project directory:
```bash
cd C:\Users\CHAYAN\.gemini\antigravity\scratch\ca_agent_workshop
```

### 2. (Optional) Set your API key if using Gemini Flash:
```bash
# In PowerShell:
$env:GEMINI_API_KEY="your-gemini-api-key"
```
*(You can also simply type the key directly into the sidebar in the web app)*

### 3. Launch the Web Dashboard:
```bash
streamlit run app.py
```

---

## 📁 Project Architecture

```
ca_agent_workshop/
│
├── app.py                      # Interactive Streamlit Web UI (5 feature tabs)
├── agent.py                    # Lightweight CA Agent Orchestrator (Gemini / Ollama / Groq / Offline)
├── schemas.py                  # Pydantic data models & robust fallback classes
│
├── tools/
│   ├── tax_rules.py            # Arithmetic validation, GSTIN checksums, Section 17(5) ITC rules
│   ├── reconciliation.py       # Bank transaction matching with TDS awareness
│   └── financial_ratios.py     # Solvency, liquidity, and profitability ratio engines
│
├── sample_data/
│   ├── sample_invoices.json    # 3 preset invoices (Valid, Math Mismatch, Blocked ITC)
│   ├── sample_bank_statement.csv # Realistic bank transactions for reconciliation
│   └── sample_financials.json  # Balance sheet & P&L figures for diagnostics
│
└── requirements.txt            # Dependency list
```

---

## 🎯 Workshop Agenda Guide (How to Present It)

- **Minute 0–15:** Introduce Agentic AI vs simple chat: Why CAs need deterministic validation tools alongside LLMs (LLMs extract, Python checks the math).
- **Minute 15–35 (Tab 1):** Demonstrate invoice extraction on the 3 preset samples. Show how it immediately flags the ₹2,600 billing error in Sample 2 and flags blocked ITC in Sample 3!
- **Minute 35–55 (Tab 2):** Run Bank Reconciliation: show 3-way matching and how TDS deductions are accounted for automatically.
- **Minute 55–75 (Tab 3 & 4):** Review Financial Ratios and test the statutory tax chat.
- **Minute 75–90 (Hands-on):** Have attendees write a new rule in `tools/tax_rules.py` (e.g., adding an audit rule for invoices exceeding ₹2,00,000 requiring PAN declaration).
