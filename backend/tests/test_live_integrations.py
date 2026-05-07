"""Live integration tests — call real external APIs.

Run with:
    $env:RUN_LIVE_API_TESTS="1"
    python -m pytest backend/tests/test_live_integrations.py -q
"""

import os
from pathlib import Path

import fitz
import pytest

from app.core.config import Settings
from app.services.action_planner import generate_action_plan
from app.services.extractor import extract_judgment
from app.services.llm_client import GeminiClient
from app.services.sarvam_client import SarvamClient


pytestmark = pytest.mark.live_api


def live_enabled() -> bool:
    return os.getenv("RUN_LIVE_API_TESTS") == "1"


def live_settings() -> Settings:
    settings = Settings()
    if not settings.sarvam_api_key or settings.sarvam_api_key.startswith("replace_with"):
        pytest.skip("SARVAM_API_KEY is not configured.")
    if not settings.openrouter_api_key or settings.openrouter_api_key.startswith("replace_with"):
        pytest.skip("OPENROUTER_API_KEY is not configured.")
    return settings


# ---------------------------------------------------------------------------
# Sarvam Translate
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not live_enabled(), reason="Set RUN_LIVE_API_TESTS=1 to call external APIs.")
@pytest.mark.asyncio
async def test_sarvam_translate_api_is_working() -> None:
    settings = live_settings()
    translated = await SarvamClient(settings).translate_to_kannada(
        "The department must comply with the court order."
    )
    assert isinstance(translated, str)
    assert len(translated.strip()) > 0


# ---------------------------------------------------------------------------
# Sarvam Document Intelligence — create job only (fast smoke test, step 1/5)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not live_enabled(), reason="Set RUN_LIVE_API_TESTS=1 to call external APIs.")
@pytest.mark.asyncio
async def test_sarvam_document_intelligence_job_creation() -> None:
    """Verify that Sarvam accepts a new DI job (steps 1 only, no upload)."""
    settings = live_settings()
    job = await SarvamClient(settings).create_document_intelligence_job(
        language="en-IN", output_format="md"
    )
    assert job.get("job_id"), f"Expected job_id in response, got: {job}"
    assert job.get("job_state") in {"Accepted", "Pending", "Running", "Completed"}, (
        f"Unexpected job_state: {job.get('job_state')}"
    )


# ---------------------------------------------------------------------------
# Sarvam Document Intelligence — full pipeline on a synthesised scanned PDF
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not live_enabled(), reason="Set RUN_LIVE_API_TESTS=1 to call external APIs.")
@pytest.mark.asyncio
async def test_sarvam_ocr_pdf_scanned_document(tmp_path: Path) -> None:
    """Full DI pipeline: create → upload → start → poll → download → verify text."""
    settings = live_settings()
    # Build a minimal text PDF that Sarvam will treat as OCR-able.
    pdf_path = tmp_path / "scan_like.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(
        fitz.Rect(72, 72, 540, 760),
        "High Court of Karnataka\nW.P. No. 9999 of 2026\nCompliance required within 30 days.",
        fontsize=12,
    )
    doc.save(pdf_path)

    text = await SarvamClient(settings).ocr_pdf(pdf_path)
    assert isinstance(text, str)
    assert len(text.strip()) > 0, "OCR returned empty text"


# ---------------------------------------------------------------------------
# OpenRouter / Gemini Flash
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not live_enabled(), reason="Set RUN_LIVE_API_TESTS=1 to call external APIs.")
@pytest.mark.asyncio
async def test_openrouter_gemini_flash_json_completion_is_working() -> None:
    settings = live_settings()
    result = await GeminiClient(settings).json_completion(
        "Return ONLY valid JSON.",
        'Return {"service":"gemini","ok":true}.',
    )
    assert result["ok"] is True
    assert result["service"] == "gemini"


# ---------------------------------------------------------------------------
# End-to-end: text-based judgment PDF — no OCR path
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not live_enabled(), reason="Set RUN_LIVE_API_TESTS=1 to call external APIs.")
@pytest.mark.asyncio
async def test_text_based_judgment_pdf_extracts_without_ocr(tmp_path: Path) -> None:
    settings = live_settings()
    pdf_path = tmp_path / "text_judgment.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(
        fitz.Rect(72, 72, 540, 760),
        """
        IN THE HIGH COURT OF KARNATAKA AT BENGALURU
        DATED THIS THE 5th DAY OF MAY, 2026
        W.P. No. 1234 of 2026
        BETWEEN: Sri Test Petitioner
        AND: State of Karnataka, Revenue Department
        ORDER
        The respondent Revenue Department shall consider the representation of the petitioner
        and pass appropriate orders within seven days from receipt of this order.
        The Legal Cell may examine whether an appeal is required within 30 days.
        Compliance shall be reported to the Department Secretary.
        """,
        fontsize=11,
    )
    doc.save(pdf_path)

    extraction, field_meta, ocr_used, confidence = await extract_judgment(pdf_path, settings)
    action_plan = await generate_action_plan(extraction, settings)

    assert ocr_used is False
    assert extraction.case_number
    assert extraction.directives
    assert action_plan
    assert confidence > 0
    assert field_meta["case_number"]["source"] in {"BOTH", "RULE", "CONFLICT"}
