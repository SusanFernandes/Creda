"""
Form 16 PDF text extraction (MVP) — uses pypdf only (no pdfplumber) to avoid dependency pins.

Extracts common labels from Indian Form 16 Part B text. Values are hints for profile upsert.
"""
from __future__ import annotations

import re
from typing import Any


def parse_form16_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """Return suggested profile fields + raw snippets for review."""
    out: dict[str, Any] = {
        "ok": False,
        "suggested": {},
        "notes": [],
        "raw_preview": "",
    }
    try:
        from pypdf import PdfReader
        from io import BytesIO

        reader = PdfReader(BytesIO(pdf_bytes))
        texts: list[str] = []
        for page in reader.pages[:8]:
            t = page.extract_text() or ""
            texts.append(t)
        raw = "\n".join(texts)
        out["raw_preview"] = raw[:4000]
        if not raw.strip():
            out["notes"].append("No text extracted — PDF may be scanned image-only.")
            return out

        def _money(label_patterns: list[str]) -> float | None:
            for pat in label_patterns:
                m = re.search(pat, raw, re.I | re.M)
                if m:
                    num = m.group(1).replace(",", "").strip()
                    try:
                        return float(num)
                    except ValueError:
                        continue
            return None

        gross = _money([
            r"(?:Gross\s+Salary|Income\s+from\s+Salary|Gross\s+Income)[^\d]{0,40}([\d,]+(?:\.\d+)?)",
            r"(?:Total\s+Salary|Aggregate\s+of\s+Salary)[^\d]{0,40}([\d,]+(?:\.\d+)?)",
        ])
        basic = _money([
            r"Basic\s+Salary[^\d]{0,30}([\d,]+(?:\.\d+)?)",
            r"Basic\s+Pay[^\d]{0,30}([\d,]+(?:\.\d+)?)",
        ])
        hra = _money([
            r"(?:House\s+Rent\s+Allowance|HRA)[^\d]{0,30}([\d,]+(?:\.\d+)?)",
        ])
        nps = _money([
            r"(?:NPS|80\s*CCD)[^\d]{0,40}([\d,]+(?:\.\d+)?)",
        ])
        sec80c = _money([
            r"(?:Section\s*80C|80\s*C)[^\d]{0,40}([\d,]+(?:\.\d+)?)",
        ])

        suggested: dict[str, float] = {}
        if gross and gross > 0:
            suggested["annual_gross_from_form16"] = gross
            suggested["monthly_income_hint"] = round(gross / 12, 2)
        if basic and basic > 0:
            suggested["basic_salary_monthly_hint"] = round(basic / 12, 2)
        if hra and hra > 0:
            suggested["hra_monthly_hint"] = round(hra / 12, 2)
        if nps and nps > 0:
            suggested["nps_contribution_hint"] = nps
        if sec80c and sec80c > 0:
            suggested["section_80c_amount_hint"] = sec80c

        out["suggested"] = suggested
        out["ok"] = bool(suggested)
        if not suggested:
            out["notes"].append("Could not confidently parse salary fields — check raw_preview.")
        return out
    except Exception as e:
        out["notes"].append(f"Parse error: {e}")
        return out
