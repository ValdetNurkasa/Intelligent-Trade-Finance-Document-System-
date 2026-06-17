from __future__ import annotations
from pathlib import Path

import fitz  # PyMuPDF


def extract_text(file_path: Path) -> str:
    """Return concatenated text from all pages."""
    try:
        doc = fitz.open(str(file_path))
        return "\n".join(page.get_text() for page in doc)
    except Exception:
        return ""


def extract_pages(file_path: Path) -> list[dict]:
    """
    Return per-page data: text + word bounding boxes.
    Each entry: {page_num, text, words: [{text, bbox: [x0,y0,x1,y1]}]}.
    """
    try:
        doc = fitz.open(str(file_path))
        pages = []
        for i, page in enumerate(doc, 1):
            text = page.get_text()
            words = []
            for x0, y0, x1, y1, word, *_ in page.get_text("words"):
                words.append({"text": word, "bbox": [x0, y0, x1, y1]})
            pages.append({"page_num": i, "text": text, "words": words})
        return pages
    except Exception:
        return []


def render_page_image(file_path: Path, page_index: int = 0, dpi: int = 150) -> bytes:
    """Render a PDF page to PNG bytes for the OCR path. page_index is 0-based."""
    doc = fitz.open(str(file_path))
    idx = min(page_index, len(doc) - 1)
    page = doc[idx]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")
