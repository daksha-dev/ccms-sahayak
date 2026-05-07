from pathlib import Path

import fitz

from app.services.pdf_parser import parse_digital_pdf, scanned_pages_as_base64


def test_text_pdf_with_short_page_is_not_routed_to_ocr(tmp_path: Path) -> None:
    path = tmp_path / "short_text.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Short text")
    doc.save(path)

    parsed = parse_digital_pdf(path)

    assert parsed.scanned_pages == []
    assert parsed.ocr_required is False


def test_image_only_page_is_rendered_for_ocr_without_poppler(tmp_path: Path) -> None:
    path = tmp_path / "blank_scan_like.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(path)

    parsed = parse_digital_pdf(path)
    encoded = scanned_pages_as_base64(path, parsed.scanned_pages)

    assert parsed.scanned_pages == [1]
    assert encoded[0]["page"] == 1
    assert len(encoded[0]["image_base64"]) > 100
