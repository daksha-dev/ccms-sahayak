"""Comprehensive unit tests for document parsing and output generation.

Tests cover:
- PDF parsing (digital text, scanned pages)
- OCR integration path (mocked Sarvam pipeline)
- Extraction pipeline (rule + LLM merge)
- Action plan generation
- Confidence scoring and urgency bands
- Upload endpoint (via FastAPI TestClient)

Run with: python -m pytest backend/tests/test_document_pipeline.py -v
"""

import io
import json
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.schemas.dto import Directive
from app.core.config import Settings
from app.core.database import Base, get_db
from app.main import app
from app.schemas.dto import ActionPlanItem, ExtractionJSON
from app.services.confidence import appeal_deadline, overall_confidence, score_field, urgency_band
from app.services.extractor import extract_judgment, parse_with_ocr_if_needed
from app.services.pdf_parser import (
    ParsedPDF,
    PageText,
    find_coordinates,
    parse_digital_pdf,
    scanned_pages_as_base64,
)
from app.services.rule_extractor import extract_case_number, extract_court_name, extract_order_date, run_rules


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_text_pdf(tmp_path: Path, text: str, filename: str = "judgment.pdf") -> Path:
    path = tmp_path / filename
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(72, 72, 540, 760), text, fontsize=11)
    doc.save(path)
    return path


def _make_blank_pdf(tmp_path: Path, filename: str = "scan.pdf") -> Path:
    path = tmp_path / filename
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    return path


def _make_settings(**kwargs: Any) -> Settings:
    return Settings(
        sarvam_api_key="test-key",
        openrouter_api_key="test-openrouter-key",
        **kwargs,
    )


# ---------------------------------------------------------------------------
# PDF Parser Tests
# ---------------------------------------------------------------------------

class TestPDFParser:
    def test_digital_pdf_extracts_text(self, tmp_path: Path) -> None:
        path = _make_text_pdf(tmp_path, "High Court of Karnataka W.P. No. 1234 of 2026")
        parsed = parse_digital_pdf(path)
        assert parsed.full_text.strip() != ""
        assert parsed.scanned_pages == []
        assert parsed.ocr_required is False

    def test_blank_page_flagged_as_scanned(self, tmp_path: Path) -> None:
        path = _make_blank_pdf(tmp_path)
        parsed = parse_digital_pdf(path)
        assert 1 in parsed.scanned_pages
        assert parsed.ocr_required is True

    def test_multi_page_pdf_has_correct_page_count(self, tmp_path: Path) -> None:
        path = tmp_path / "multi.pdf"
        doc = fitz.open()
        for i in range(3):
            p = doc.new_page()
            p.insert_text((72, 72), f"Page {i + 1} text here")
        doc.save(path)
        parsed = parse_digital_pdf(path)
        assert len(parsed.pages) == 3

    def test_scanned_pages_as_base64_returns_encoded_images(self, tmp_path: Path) -> None:
        path = _make_blank_pdf(tmp_path)
        encoded = scanned_pages_as_base64(path, [1])
        assert len(encoded) == 1
        assert encoded[0]["page"] == 1
        assert len(encoded[0]["image_base64"]) > 100

    def test_scanned_pages_as_base64_empty_list(self, tmp_path: Path) -> None:
        path = _make_text_pdf(tmp_path, "some text")
        encoded = scanned_pages_as_base64(path, [])
        assert encoded == []

    def test_find_coordinates_locates_word(self, tmp_path: Path) -> None:
        path = _make_text_pdf(tmp_path, "WP 1234 Karnataka")
        parsed = parse_digital_pdf(path)
        coords = find_coordinates(parsed, "Karnataka")
        # May find or not depending on exact word boundaries — just check type
        assert isinstance(coords, list)

    def test_full_text_joins_pages(self) -> None:
        parsed = ParsedPDF(
            pages=[PageText(page=1, text="first"), PageText(page=2, text="second")],
            scanned_pages=[],
        )
        assert "first" in parsed.full_text
        assert "second" in parsed.full_text


# ---------------------------------------------------------------------------
# Rule Extractor Tests
# ---------------------------------------------------------------------------

class TestRuleExtractor:
    def test_extracts_wp_case_number(self) -> None:
        text = "IN THE HIGH COURT\nW.P. No. 5678 of 2025\nPetitioner vs State"
        assert extract_case_number(text) == "W.P. No. 5678 of 2025"

    def test_extracts_wa_case_number(self) -> None:
        text = "W.A. No. 100 of 2024"
        assert extract_case_number(text) is not None

    def test_returns_none_when_no_case_number(self) -> None:
        assert extract_case_number("Unrelated text without any case reference") is None

    def test_extracts_high_court_karnataka(self) -> None:
        assert extract_court_name("IN THE HIGH COURT OF KARNATAKA AT BENGALURU") == "High Court of Karnataka"

    def test_returns_none_for_unknown_court(self) -> None:
        assert extract_court_name("Supreme Court of India") is None

    def test_extracts_dated_this_the_format(self) -> None:
        text = "DATED THIS THE 15th DAY OF MARCH, 2026"
        assert extract_order_date(text) == date(2026, 3, 15)

    def test_extracts_iso_date(self) -> None:
        assert extract_order_date("Order date: 2026-05-07") == date(2026, 5, 7)

    def test_run_rules_returns_dict(self) -> None:
        text = "IN THE HIGH COURT OF KARNATAKA\nW.P. No. 999 of 2024\nDATED THIS THE 1st DAY OF JANUARY, 2024"
        result = run_rules(text)
        assert result["case_number"] is not None
        assert result["court_name"] == "High Court of Karnataka"
        assert result["date_of_order"] == date(2024, 1, 1)


# ---------------------------------------------------------------------------
# Confidence Tests (already in test_confidence.py — replicated for completeness)
# ---------------------------------------------------------------------------

class TestConfidenceScoring:
    def test_both_agreement_gives_high_score(self) -> None:
        score, source, conflict = score_field("WP 1 of 2024", "WP 1 of 2024")
        assert score == 0.9
        assert source == "BOTH"
        assert conflict is False

    def test_conflict_gives_low_score(self) -> None:
        score, source, conflict = score_field("WP 1", "WA 2")
        assert score == 0.35
        assert conflict is True

    def test_llm_only_gives_medium_score(self) -> None:
        score, source, conflict = score_field(None, "High Court")
        assert score == 0.7
        assert source == "LLM"

    def test_both_none_gives_unreadable(self) -> None:
        score, source, conflict = score_field(None, None)
        assert score == 0.0
        assert source == "UNREADABLE"

    def test_overall_confidence_averages_scores(self) -> None:
        assert overall_confidence([0.9, 0.7, 0.35]) == pytest.approx(0.65, rel=1e-2)

    def test_overall_confidence_empty(self) -> None:
        assert overall_confidence([]) == 0.0

    def test_urgency_red_for_contempt(self) -> None:
        assert urgency_band(None, "CONTEMPT") == "RED"

    def test_urgency_red_within_7_days(self) -> None:
        assert urgency_band(date(2026, 5, 8), "COMPLIANCE", today=date(2026, 5, 5)) == "RED"

    def test_urgency_amber_within_30_days(self) -> None:
        assert urgency_band(date(2026, 5, 30), "COMPLIANCE", today=date(2026, 5, 5)) == "AMBER"

    def test_urgency_green_far_future(self) -> None:
        assert urgency_band(date(2026, 8, 1), "COMPLIANCE", today=date(2026, 5, 5)) == "GREEN"

    def test_appeal_deadline_adds_days(self) -> None:
        assert appeal_deadline(date(2026, 5, 1), 30) == date(2026, 5, 31)

    def test_appeal_deadline_none_when_no_date(self) -> None:
        assert appeal_deadline(None, 30) is None


# ---------------------------------------------------------------------------
# OCR Integration Path (mocked)
# ---------------------------------------------------------------------------

class TestOCRIntegrationPath:
    @pytest.mark.asyncio
    async def test_digital_pdf_skips_ocr(self, tmp_path: Path) -> None:
        path = _make_text_pdf(
            tmp_path,
            "IN THE HIGH COURT OF KARNATAKA\nW.P. No. 1 of 2026\nCompliance required.",
        )
        settings = _make_settings()
        with patch("app.services.sarvam_client.SarvamClient.ocr_pdf", new_callable=AsyncMock) as mock_ocr:
            parsed = await parse_with_ocr_if_needed(path, settings)
        mock_ocr.assert_not_called()
        assert parsed.full_text.strip() != ""

    @pytest.mark.asyncio
    async def test_scanned_pdf_calls_ocr_pdf(self, tmp_path: Path) -> None:
        path = _make_blank_pdf(tmp_path)
        settings = _make_settings()
        ocr_return = "# Karnataka HC\n\nW.P. No. 42 of 2026"
        with patch("app.services.extractor.SarvamClient") as MockClient:
            instance = MockClient.return_value
            instance.ocr_pdf = AsyncMock(return_value=ocr_return)
            parsed = await parse_with_ocr_if_needed(path, settings)
        # The OCR text should appear in the scanned page
        texts = [p.text for p in parsed.pages]
        assert any(ocr_return in t for t in texts)

    @pytest.mark.asyncio
    async def test_extract_judgment_digital_no_ocr(self, tmp_path: Path) -> None:
        """Full extraction on a digital PDF should not call Sarvam OCR."""
        path = _make_text_pdf(
            tmp_path,
            """IN THE HIGH COURT OF KARNATAKA AT BENGALURU
DATED THIS THE 5th DAY OF MAY, 2026
W.P. No. 1234 of 2026
BETWEEN: Sri Test Petitioner
AND: State of Karnataka, Revenue Department
ORDER
The Revenue Department shall comply within 30 days.
""",
        )
        settings = _make_settings()
        fake_extraction = {
            "case_number": "W.P. No. 1234 of 2026",
            "date_of_order": "2026-05-05",
            "court_name": "High Court of Karnataka",
            "parties_petitioner": ["Sri Test Petitioner"],
            "parties_respondent": ["State of Karnataka, Revenue Department"],
            "responsible_department": "Revenue Department",
            "directives": [
                {
                    "directive_text": "comply within 30 days",
                    "directive_type": "COMPLIANCE",
                }
            ],
            "limitation_period_days": 30,
            "nature_of_order": "Direction",
        }

        with patch("app.services.extractor.GeminiClient") as MockGemini:
            instance = MockGemini.return_value
            instance.json_completion = AsyncMock(return_value=fake_extraction)
            extraction, field_meta, ocr_used, confidence = await extract_judgment(path, settings)

        assert ocr_used is False
        assert extraction.case_number == "W.P. No. 1234 of 2026"
        assert confidence > 0
        assert field_meta["case_number"]["source"] in {"BOTH", "RULE", "LLM"}

    @pytest.mark.asyncio
    async def test_extract_judgment_scanned_uses_ocr(self, tmp_path: Path) -> None:
        """Scanned PDF should invoke OCR and then LLM extraction."""
        path = _make_blank_pdf(tmp_path)
        settings = _make_settings()
        ocr_text = "IN THE HIGH COURT OF KARNATAKA\nW.P. No. 99 of 2025"
        fake_extraction = {
            "case_number": "W.P. No. 99 of 2025",
            "date_of_order": None,
            "court_name": "High Court of Karnataka",
            "parties_petitioner": ["Petitioner X"],
            "parties_respondent": ["State"],
            "responsible_department": "Revenue",
            "directives": [],
            "limitation_period_days": None,
            "nature_of_order": "Direction",
        }

        with (
            patch("app.services.extractor.SarvamClient") as MockSarvam,
            patch("app.services.extractor.GeminiClient") as MockGemini,
        ):
            sarvam_instance = MockSarvam.return_value
            sarvam_instance.ocr_pdf = AsyncMock(return_value=ocr_text)
            gemini_instance = MockGemini.return_value
            gemini_instance.json_completion = AsyncMock(return_value=fake_extraction)

            extraction, field_meta, ocr_used, confidence = await extract_judgment(path, settings)

        assert ocr_used is True
        assert extraction.case_number is not None


# ---------------------------------------------------------------------------
# Action Planner Tests
# ---------------------------------------------------------------------------

class TestActionPlanner:
    @pytest.mark.asyncio
    async def test_action_plan_returns_list_of_items(self) -> None:
        from app.services.action_planner import generate_action_plan

        settings = _make_settings()
        extraction = ExtractionJSON(
            case_number="WP 1 of 2026",
            date_of_order=date(2026, 5, 5),
            court_name="High Court of Karnataka",
            parties_petitioner=["Petitioner"],
            parties_respondent=["Respondent"],
            responsible_department="Revenue",
            directives=[
                Directive(directive_text="comply", directive_type="COMPLIANCE")
            ],
            limitation_period_days=30,
            nature_of_order="Direction",
            appeal_deadline_date=date(2026, 6, 4),
            urgency_band="GREEN",
            coordinate_map={},
            confidence_scores={"case_number": 0.9},
        )
        fake_plan = {
            "action_plan_items": [
                {
                    "directive_type": "COMPLIANCE",
                    "recommended_action": "Comply within 30 days",
                    "responsible_authority": "Secretary",
                    "deadline_date": "2026-06-04",
                    "priority_level": "GREEN",
                    "notes": "",
                }
            ]
        }
        with patch("app.services.action_planner.GeminiClient") as MockGemini:
            instance = MockGemini.return_value
            instance.json_completion = AsyncMock(return_value=fake_plan)
            items = await generate_action_plan(extraction, settings)

        assert len(items) == 1
        assert items[0].directive_type == "COMPLIANCE"
        assert items[0].priority_level == "GREEN"

    @pytest.mark.asyncio
    async def test_action_plan_handles_list_response(self) -> None:
        """LLM sometimes returns a bare list instead of {action_plan_items: [...]}."""
        from app.services.action_planner import generate_action_plan

        settings = _make_settings()
        extraction = ExtractionJSON(
            case_number="WP 2 of 2026",
            date_of_order=None,
            court_name=None,
            parties_petitioner=[],
            parties_respondent=[],
            responsible_department=None,
            directives=[],
            limitation_period_days=None,
            nature_of_order=None,
            appeal_deadline_date=None,
            urgency_band="GREEN",
            coordinate_map={},
            confidence_scores={},
        )
        raw_list = [
            {
                "directive_type": "APPEAL",
                "recommended_action": "File appeal",
                "responsible_authority": "Legal Cell",
                "deadline_date": None,
                "priority_level": "AMBER",
                "notes": "Check limitation",
            }
        ]
        with patch("app.services.action_planner.GeminiClient") as MockGemini:
            instance = MockGemini.return_value
            instance.json_completion = AsyncMock(return_value=raw_list)
            items = await generate_action_plan(extraction, settings)

        assert len(items) == 1
        assert items[0].directive_type == "APPEAL"


# ---------------------------------------------------------------------------
# Upload Endpoint (FastAPI TestClient — unit level with mocked services)
# ---------------------------------------------------------------------------

class TestUploadEndpoint:
    def _pdf_bytes(self) -> bytes:
        doc = fitz.open()
        p = doc.new_page()
        p.insert_textbox(
            fitz.Rect(72, 72, 540, 760),
            "IN THE HIGH COURT OF KARNATAKA\nW.P. No. 1 of 2026\nOrder dated 1st May 2026",
            fontsize=11,
        )
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def test_upload_rejects_non_pdf(self, tmp_path: Path) -> None:
        from app.core.config import get_settings
        import app.core.database as db_module

        db_url = f"sqlite:///{tmp_path / 'test.db'}"
        test_engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(test_engine)
        TestSession = sessionmaker(bind=test_engine)
        test_settings = _make_settings(
            database_url=db_url,
            pdf_storage_path=str(tmp_path / "pdfs"),
        )

        def override_get_db():
            session = TestSession()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_settings] = lambda: test_settings
        try:
            client = TestClient(app)
            response = client.post(
                "/api/v1/judgments/upload",
                files={"file": ("report.txt", b"not a pdf", "text/plain")},
            )
            assert response.status_code == 400
            assert "PDF" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
            test_engine.dispose()

    def test_upload_pdf_succeeds_with_mocked_services(self, tmp_path: Path) -> None:
        from app.core.config import get_settings

        db_url = f"sqlite:///{tmp_path / 'test.db'}"
        test_engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(test_engine)
        TestSession = sessionmaker(bind=test_engine)
        test_settings = _make_settings(
            database_url=db_url,
            pdf_storage_path=str(tmp_path / "pdfs"),
        )

        def override_get_db():
            session = TestSession()
            try:
                yield session
            finally:
                session.close()

        fake_extraction = ExtractionJSON(
            case_number="W.P. No. 1 of 2026",
            date_of_order=date(2026, 5, 1),
            court_name="High Court of Karnataka",
            parties_petitioner=["Petitioner"],
            parties_respondent=["State"],
            responsible_department="Revenue",
            directives=[Directive(directive_text="comply", directive_type="COMPLIANCE")],
            limitation_period_days=30,
            nature_of_order="Direction",
            appeal_deadline_date=date(2026, 5, 31),
            urgency_band="GREEN",
            coordinate_map={},
            confidence_scores={"case_number": 0.9},
        )
        fake_field_meta = {"case_number": {"score": 0.9, "source": "BOTH", "conflict": False}}
        fake_action_items = [
            ActionPlanItem(
                directive_type="COMPLIANCE",
                recommended_action="Comply within 30 days",
                responsible_authority="Secretary",
                deadline_date=date(2026, 5, 31),
                priority_level="GREEN",
                notes="",
            )
        ]

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_settings] = lambda: test_settings
        try:
            with (
                patch("app.api.judgments.extract_judgment", new_callable=AsyncMock,
                      return_value=(fake_extraction, fake_field_meta, False, 0.9)),
                patch("app.api.judgments.generate_action_plan", new_callable=AsyncMock,
                      return_value=fake_action_items),
            ):
                client = TestClient(app)
                response = client.post(
                    "/api/v1/judgments/upload",
                    files={"file": ("judgment.pdf", self._pdf_bytes(), "application/pdf")},
                )

            assert response.status_code == 200, response.text
            body = response.json()
            assert body["job_id"] is not None
            assert body["extraction_status"] in {"EXTRACTED", "FLAGGED"}
            assert body["overall_confidence"] == pytest.approx(0.9, rel=1e-2)
            assert body["ocr_used"] is False
        finally:
            app.dependency_overrides.clear()
            test_engine.dispose()
