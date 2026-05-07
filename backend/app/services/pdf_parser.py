import base64
from dataclasses import dataclass, field
from pathlib import Path

import fitz


@dataclass
class PageText:
    page: int
    text: str
    words: list[dict] = field(default_factory=list)


@dataclass
class ParsedPDF:
    pages: list[PageText]
    scanned_pages: list[int]

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)

    @property
    def ocr_required(self) -> bool:
        return bool(self.scanned_pages)


def parse_digital_pdf(path: Path) -> ParsedPDF:
    doc = fitz.open(path)
    pages: list[PageText] = []
    scanned_pages: list[int] = []
    for index, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        words = [
            {"text": word[4], "bbox": [word[0], word[1], word[2], word[3]], "page": index}
            for word in page.get_text("words")
        ]
        if len(text) < 100 and not words:
            scanned_pages.append(index)
        pages.append(PageText(page=index, text=text, words=words))
    return ParsedPDF(pages=pages, scanned_pages=scanned_pages)


def scanned_pages_as_base64(path: Path, pages: list[int]) -> list[dict]:
    if not pages:
        return []
    requested = set(pages)
    encoded = []
    doc = fitz.open(path)
    zoom = 300 / 72
    matrix = fitz.Matrix(zoom, zoom)
    for page_number in sorted(requested):
        if page_number < 1 or page_number > len(doc):
            continue
        pixmap = doc[page_number - 1].get_pixmap(matrix=matrix, alpha=False)
        encoded.append({"page": page_number, "image_base64": base64.b64encode(pixmap.tobytes("png")).decode("ascii")})
    return encoded


def find_coordinates(parsed: ParsedPDF, field_value: str | None) -> list[dict]:
    if not field_value:
        return []
    needle = field_value.lower()
    for page in parsed.pages:
        matches = [word for word in page.words if word["text"].lower() in needle or needle in word["text"].lower()]
        if matches:
            return [{"page": page.page, "bbox": matches[0]["bbox"]}]
    return []
