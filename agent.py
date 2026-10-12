"""
Lightweight Chartered Accountant (CA) Agent Orchestrator.
Supports:
1. Google Gemini Flash (e.g., gemini-1.5-flash / gemini-2.0-flash / gemini-2.5-flash)
2. Ollama / Local Small Language Models (e.g., llama3.2:3b, qwen2.5:3b, phi3)
3. Groq API (llama-3.1-8b-instant)
4. Offline / Sandbox Heuristic Mode (for zero-setup workshop demonstrations)
"""
import os
import json
import base64
import re
from typing import Dict, Any, Optional, Tuple, List
import requests

from schemas import ExtractedInvoice, InvoiceItem, AuditReport
from tools.tax_rules import audit_invoice

EXTRACTION_SYSTEM_PROMPT = """You are a senior Chartered Accountant (CA) AI assistant specializing in tax audits, invoice processing, and statutory compliance.
Analyze the provided invoice image or text and extract the data into pure, valid JSON with this exact schema:
{
  "invoice_number": "string",
  "invoice_date": "YYYY-MM-DD or string",
  "due_date": "YYYY-MM-DD or null",
  "vendor_name": "string",
  "vendor_tax_id": "string (GSTIN/VAT/EIN/Tax ID if visible)",
  "customer_name": "string",
  "customer_tax_id": "string or null",
  "expense_category": "string (e.g. IT Services, Office Supplies, Food & Dining, Travel, Machinery, Professional Fees, Luxury, Personal)",
  "items": [
    {
      "description": "string",
      "hsn_sac_code": "string",
      "quantity": 1.0,
      "unit_price": 0.0,
      "tax_rate_pct": 18.0,
      "line_total": 0.0
    }
  ],
  "subtotal": 0.0,
  "cgst": 0.0,
  "sgst": 0.0,
  "igst": 0.0,
  "total_tax": 0.0,
  "grand_total": 0.0,
  "currency": "INR"
}
Output ONLY the JSON object. Do not wrap in markdown or add explanations.
"""

TAX_ADVISORY_SYSTEM_PROMPT = """You are an experienced Chartered Accountant (CA) advisor. 
You advise businesses on corporate tax, GST (Goods & Services Tax), TDS (Tax Deducted at Source), depreciation schedules, and audit requirements.
Give clear, concise, statutory-referenced, bulleted guidance. 
Mention relevant sections where applicable (e.g., Section 194C, 194J, 194I for TDS, Section 17(5) for blocked GST ITC, Section 32 for Depreciation).
Keep responses sharp and practical for finance teams.
"""

class CAAgent:
    def __init__(
        self,
        provider: str = "sarvam", # "sarvam", "gemini_flash", "openai_compatible", "ollama", "groq", "offline"
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        endpoint_url: Optional[str] = None
    ):
        # Auto-load .env if available
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        if k not in os.environ:
                            os.environ[k] = v

        self.provider = provider
        self.api_key = api_key or os.environ.get("SARVAM_API_KEY") or os.environ.get("CUSTOM_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY", "")
        self.endpoint_url = endpoint_url or "https://api.sarvam.ai/v1"
        
        # Default lightweight models
        if not model_name:
            if provider == "sarvam":
                self.model_name = "sarvam-105b-conversations"
            elif provider == "gemini_flash":
                self.model_name = "gemini-1.5-flash"
            elif provider == "groq":
                self.model_name = "llama-3.1-8b-instant"
            elif provider == "ollama":
                self.model_name = "llama3.2:3b"
            elif provider == "openai_compatible":
                self.model_name = "gpt-4o-mini"
            else:
                self.model_name = "offline-rules"
        else:
            self.model_name = model_name

    def extract_invoice_data(
        self,
        file_bytes: Optional[bytes] = None,
        mime_type: str = "image/png",
        raw_text: Optional[str] = None
    ) -> ExtractedInvoice:
        """
        Extracts structured invoice information using the selected lightweight engine.
        """
        # If offline or no API key provided for cloud models, fallback to deterministic parser
        if self.provider == "offline" or (self.provider in ["sarvam", "gemini_flash", "groq"] and not self.api_key):
            return self._heuristic_offline_extract(raw_text or "Sample Invoice Text")

        try:
            if self.provider == "sarvam":
                return self._call_sarvam(raw_text or "No text provided")
            elif self.provider == "gemini_flash":
                return self._call_gemini_flash(file_bytes, mime_type, raw_text)
            elif self.provider == "groq":
                return self._call_groq(raw_text or "No text provided")
            elif self.provider == "openai_compatible":
                return self._call_openai_compatible(raw_text or "No text provided")
            elif self.provider == "ollama":
                return self._call_ollama(raw_text or "No text provided")
            else:
                return self._heuristic_offline_extract(raw_text or "")
        except Exception as e:
            print(f"[CAAgent Warning] Lightweight model call failed: {e}. Falling back to heuristic extractor.")
            return self._heuristic_offline_extract(raw_text or "", error_note=str(e))

    def _call_sarvam(self, text: str) -> ExtractedInvoice:
        """Calls Sarvam AI (e.g. sarvam-105b-conversations) via sovereign API."""
        url = f"{self.endpoint_url.rstrip('/')}/chat/completions"
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name or "sarvam-105b-conversations",
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract structured invoice JSON:\n{text}"}
            ],
            "temperature": 0.1
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=35)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return self._clean_and_parse_json(content)

    def _call_gemini_flash(self, file_bytes: Optional[bytes], mime_type: str, raw_text: Optional[str]) -> ExtractedInvoice:
        """Calls Google Gemini 1.5 Flash via REST API (lightweight, zero-grpc)."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        
        parts = [{"text": EXTRACTION_SYSTEM_PROMPT}]
        if raw_text:
            parts.append({"text": f"Invoice text:\n{raw_text}"})
        if file_bytes:
            b64_data = base64.b64encode(file_bytes).decode("utf-8")
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": b64_data
                }
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }
        resp = requests.post(url, json=payload, timeout=45)
        resp.raise_for_status()
        data = resp.json()
        
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
        return self._clean_and_parse_json(text_out)

    def _call_groq(self, text: str) -> ExtractedInvoice:
        """Calls Groq API with lightweight 8B model."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract structured invoice JSON:\n{text}"}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return self._clean_and_parse_json(content)

    def _call_openai_compatible(self, text: str) -> ExtractedInvoice:
        """Calls custom OpenAI-compatible endpoint."""
        url = f"{self.endpoint_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract structured invoice JSON:\n{text}"}
            ],
            "temperature": 0.1
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return self._clean_and_parse_json(content)

    def _call_ollama(self, text: str) -> ExtractedInvoice:
        """Calls local Ollama server (e.g., llama3.2:3b)."""
        url = f"{self.endpoint_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract this invoice:\n{text}"}
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1}
        }
        resp = requests.post(url, json=payload, timeout=40)
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return self._clean_and_parse_json(content)

    def _clean_and_parse_json(self, raw_str: str) -> ExtractedInvoice:
        """Sanitizes LLM output and maps into ExtractedInvoice model."""
        cleaned = raw_str.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        parsed = json.loads(cleaned.strip())
        return ExtractedInvoice(**parsed)

    def _heuristic_offline_extract(self, text: str, error_note: str = "") -> ExtractedInvoice:
        """
        Deterministic regex/rule fallback extractor.
        Ensures the workshop workshop attendees can run audits even offline!
        """
        inv_match = re.search(r"(?:invoice|inv|bill)[\s#:]*([A-Za-z0-9\-\/]+)", text, re.IGNORECASE)
        inv_no = inv_match.group(1) if inv_match else "INV-2026-904"

        gstin_match = re.search(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b", text)
        gstin = gstin_match.group(1) if gstin_match else "27AABCU9603R1ZM"

        total_match = re.search(r"(?:total|grand total|net payable)[\s:]*(?:rs\.?|inr|\$)?\s*([0-9,]+\.?[0-9]*)", text, re.IGNORECASE)
        total_amt = float(total_match.group(1).replace(",", "")) if total_match else 59000.0

        vendor_match = re.search(r"(?:from|vendor|supplier|m\/s)[\s:]*([A-Za-z0-9\s\.\&]+)", text, re.IGNORECASE)
        vendor = vendor_match.group(1).strip() if vendor_match else "CloudApex Technologies Pvt Ltd"

        subtotal = round(total_amt / 1.18, 2)
        tax = round(total_amt - subtotal, 2)

        return ExtractedInvoice(
            invoice_number=inv_no,
            invoice_date="2026-10-01",
            due_date="2026-10-15",
            vendor_name=vendor.split("\n")[0][:40],
            vendor_tax_id=gstin,
            customer_name="Client Enterprise Solutions Ltd",
            customer_tax_id="29ABCDE1234F1Z5",
            expense_category="IT Services",
            items=[
                InvoiceItem(
                    description="Cloud Infrastructure & Managed DevOps Consulting",
                    hsn_sac_code="998313",
                    quantity=1.0,
                    unit_price=subtotal,
                    tax_rate_pct=18.0,
                    line_total=subtotal
                )
            ],
            subtotal=subtotal,
            cgst=round(tax / 2, 2),
            sgst=round(tax / 2, 2),
            igst=0.0,
            total_tax=tax,
            grand_total=total_amt,
            currency="INR"
        )

    def run_full_audit(self, invoice: ExtractedInvoice) -> AuditReport:
        """Executes the full automated CA audit pipeline."""
        return audit_invoice(invoice)

    def ask_tax_advisor(self, question: str) -> str:
        """Answers tax, compliance, TDS, and GST inquiries using the lightweight model."""
        if self.provider == "sarvam" and self.api_key:
            url = f"{self.endpoint_url.rstrip('/')}/chat/completions"
            headers = {
                "api-subscription-key": self.api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model_name or "sarvam-105b-conversations",
                "messages": [
                    {"role": "system", "content": TAX_ADVISORY_SYSTEM_PROMPT},
                    {"role": "user", "content": question}
                ],
                "temperature": 0.2
            }
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=30)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except Exception as e:
                return f"[Sarvam AI Notice] Could not reach Sarvam endpoint: {e}\n\n" + self._offline_tax_answer(question)
        elif self.provider == "gemini_flash" and self.api_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": TAX_ADVISORY_SYSTEM_PROMPT},
                        {"text": f"User query: {question}"}
                    ]
                }],
                "generationConfig": {"temperature": 0.2}
            }
            try:
                r = requests.post(url, json=payload, timeout=20)
                r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                return f"[API Notice] Could not reach Gemini Flash: {e}. Showing cached guidance below:\n\n" + self._offline_tax_answer(question)
        elif self.provider == "groq" and self.api_key:
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model_name,
                        "messages": [
                            {"role": "system", "content": TAX_ADVISORY_SYSTEM_PROMPT},
                            {"role": "user", "content": question}
                        ]
                    },
                    timeout=20
                )
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except Exception as e:
                return f"[API Notice] Could not reach Groq: {e}\n\n" + self._offline_tax_answer(question)
        elif self.provider == "openai_compatible" and self.api_key:
            try:
                url = f"{self.endpoint_url.rstrip('/')}/chat/completions"
                r = requests.post(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model_name,
                        "messages": [
                            {"role": "system", "content": TAX_ADVISORY_SYSTEM_PROMPT},
                            {"role": "user", "content": question}
                        ]
                    },
                    timeout=25
                )
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except Exception as e:
                return f"[API Notice] Could not reach endpoint {self.endpoint_url}: {e}\n\n" + self._offline_tax_answer(question)
        elif self.provider == "ollama":
            try:
                r = requests.post(
                    f"{self.endpoint_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": [
                            {"role": "system", "content": TAX_ADVISORY_SYSTEM_PROMPT},
                            {"role": "user", "content": question}
                        ],
                        "stream": False
                    },
                    timeout=30
                )
                r.raise_for_status()
                return r.json()["message"]["content"]
            except Exception as e:
                return f"[Ollama Notice] Could not reach local Ollama: {e}\n\n" + self._offline_tax_answer(question)
        else:
            return self._offline_tax_answer(question)

    def _offline_tax_answer(self, query: str) -> str:
        q = query.lower()
        if "tds" in q or "194" in q:
            return (
                "### 📘 Statutory TDS Summary (Income Tax Act)\n"
                "- **Sec 194C (Contractors / Subcontractors):** 1% for Individual/HUF, 2% for Companies/Firms (Threshold: ₹30,000 single or ₹1,00,000 aggregate).\n"
                "- **Sec 194J (Professional / Technical Fees):** 10% for Professional fees, 2% for Technical services & Call centers (Threshold: ₹30,000).\n"
                "- **Sec 194I (Rent):** 10% on Land/Building/Furniture, 2% on Plant & Machinery (Threshold: ₹2,40,000 per financial year).\n"
                "- **Sec 194Q (Purchase of Goods):** 0.1% for purchases exceeding ₹50 Lakhs if buyer turnover > ₹10 Crore."
            )
        elif "itc" in q or "gst" in q or "blocked" in q or "17(5)" in q:
            return (
                "### 📘 GST Input Tax Credit (ITC) Rules\n"
                "- **Section 16 Eligibility:** Inward supplies used or intended to be used in the course or furtherance of business.\n"
                "- **Section 17(5) Blocked Credits:**\n"
                "  1. Motor vehicles for passenger transport (seating capacity <= 13) unless used for taxable supply of vehicles or passenger transport.\n"
                "  2. Food & beverages, outdoor catering, beauty treatment, health services.\n"
                "  3. Club membership and gym fees.\n"
                "  4. Goods lost, stolen, destroyed, written off, or disposed of by way of gift or free samples."
            )
        elif "depreciation" in q or "asset" in q:
            return (
                "### 📘 Statutory Depreciation Rates (Companies Act & Income Tax Sec 32)\n"
                "- **Computers, Laptops & Software:** 40% (Income Tax WDV).\n"
                "- **Plant & Machinery (General):** 15%.\n"
                "- **Office Furniture & Fittings:** 10%.\n"
                "- **Commercial Motor Vehicles:** 30% (Standard Cars: 15%).\n"
                "- **Buildings (Residential):** 5% | **Commercial/Factory:** 10%."
            )
        else:
            return (
                f"### 💼 CA Advisory Response for: '{query}'\n"
                "- **Applicable Standard:** Verify standard commercial substance, tax invoicing compliance, and arm's length valuation.\n"
                "- **Audit Trail:** Maintain contemporaneous documentation, contract agreements, PO copies, and bank payment UTR numbers.\n"
                "- **Withholding Tax:** Ensure appropriate deduction of withholding taxes prior to month-end ledger closing."
            )
