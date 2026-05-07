import re
from datetime import date, datetime


CASE_RE = re.compile(r"\b(?:WP|WA|CRL|MFA|W\.P\.|W\.A\.|Crl\.P\.)\s*No\.?\s*[\w./-]+(?:\s*of\s*\d{4})?", re.I)
DATE_PATTERNS = [
    re.compile(r"dated\s+this\s+the\s+(\d{1,2})(?:st|nd|rd|th)?\s+day\s+of\s+([A-Za-z]+),?\s+(\d{4})", re.I),
    re.compile(r"\bdate\s+of\s+order\s*[:\-]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})", re.I),
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
]


def extract_case_number(text: str) -> str | None:
    match = CASE_RE.search(text)
    return " ".join(match.group(0).split()) if match else None


def extract_order_date(text: str) -> date | None:
    match = DATE_PATTERNS[0].search(text)
    if match:
        raw = f"{match.group(1)} {match.group(2)} {match.group(3)}"
        return datetime.strptime(raw, "%d %B %Y").date()
    for pattern in DATE_PATTERNS[1:]:
        match = pattern.search(text)
        if not match:
            continue
        raw = match.group(1)
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                pass
    return None


def extract_court_name(text: str) -> str | None:
    for line in text.splitlines()[:20]:
        if "high court of karnataka" in line.lower():
            return "High Court of Karnataka"
    return None


def run_rules(text: str) -> dict:
    return {
        "case_number": extract_case_number(text),
        "date_of_order": extract_order_date(text),
        "court_name": extract_court_name(text),
    }
