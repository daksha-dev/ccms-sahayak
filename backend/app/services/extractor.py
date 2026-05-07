from datetime import date
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.schemas.dto import ExtractionJSON
from app.services.confidence import appeal_deadline, overall_confidence, score_field, urgency_band
from app.services.llm_client import GeminiClient, load_prompt
from app.services.pdf_parser import ParsedPDF, find_coordinates, parse_digital_pdf
from app.services.rule_extractor import run_rules
from app.services.sarvam_client import SarvamClient


def operative_text(full_text: str, page_count: int) -> str:
    chunks = full_text.split("\n\n")
    tail = "\n\n".join(chunks[-3:]) if page_count > 3 else full_text
    lowered = full_text.lower()
    marker = max(lowered.rfind("order"), lowered.rfind("operative"))
    if marker > -1:
        return full_text[marker:] + "\n\n" + tail
    return full_text if len(full_text) < 32000 else full_text[-32000:]


async def parse_with_ocr_if_needed(path: Path, settings: Settings) -> ParsedPDF:
    parsed = parse_digital_pdf(path)
    if not parsed.scanned_pages:
        return parsed
    # Use Sarvam Document Intelligence to extract text from the whole PDF.
    # The API returns a Markdown string; we attach it to the scanned pages.
    ocr_text = await SarvamClient(settings).ocr_pdf(path)
    # Distribute the OCR text across scanned pages evenly (or all to first if
    # we cannot split).  The Markdown output does not carry per-page markers so
    # we assign the full text to every scanned page so no content is lost.
    for page in parsed.pages:
        if page.page in set(parsed.scanned_pages):
            page.text = ocr_text
    return parsed


async def extract_judgment(path: Path, settings: Settings) -> tuple[ExtractionJSON, dict[str, dict[str, Any]], bool, float]:
    parsed = await parse_with_ocr_if_needed(path, settings)
    rules = run_rules(parsed.full_text)
    prompt = load_prompt("extraction_system.txt")
    llm_payload = await GeminiClient(settings).json_completion(prompt, operative_text(parsed.full_text, len(parsed.pages)))

    field_meta: dict[str, dict[str, Any]] = {}
    values = dict(llm_payload)
    for field_name in ("case_number", "date_of_order", "court_name"):
        rule_value = rules.get(field_name)
        llm_value = values.get(field_name)
        score, source, conflict = score_field(rule_value, llm_value)
        values[field_name] = rule_value if source in {"RULE", "BOTH", "CONFLICT"} and rule_value else llm_value
        field_meta[field_name] = {"score": score, "source": source, "conflict": conflict}

    for field_name in (
        "parties_petitioner",
        "parties_respondent",
        "responsible_department",
        "directives",
        "limitation_period_days",
        "nature_of_order",
    ):
        score, source, conflict = score_field(None, values.get(field_name))
        field_meta[field_name] = {"score": score, "source": source, "conflict": conflict}

    if isinstance(values.get("date_of_order"), str):
        values["date_of_order"] = date.fromisoformat(values["date_of_order"])
    values["appeal_deadline_date"] = appeal_deadline(values.get("date_of_order"), values.get("limitation_period_days"))
    first_directive = (values.get("directives") or [{}])[0]
    values["urgency_band"] = urgency_band(values["appeal_deadline_date"], first_directive.get("directive_type"))
    values["coordinate_map"] = {
        "case_number": find_coordinates(parsed, values.get("case_number")),
        "court_name": find_coordinates(parsed, values.get("court_name")),
    }
    values["confidence_scores"] = {key: meta["score"] for key, meta in field_meta.items()}

    extraction = ExtractionJSON.model_validate(values)
    confidence = overall_confidence(list(extraction.confidence_scores.values()))
    if confidence < settings.ocr_confidence_threshold:
        field_meta["document"] = {"score": 0.0, "source": "UNREADABLE", "conflict": False}
    return extraction, field_meta, parsed.ocr_required, confidence
