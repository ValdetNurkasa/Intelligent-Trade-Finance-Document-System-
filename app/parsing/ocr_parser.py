from __future__ import annotations
import io
from pathlib import Path

try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except ImportError:
    _OCR_AVAILABLE = False

from app.parsing.pdf_parser import render_page_image

_CONFIG = r"--oem 3 --psm 6"


def _ocr_bytes(image_bytes: bytes) -> dict:
    """Run Tesseract on PNG bytes; return text, word list, avg confidence."""
    if not _OCR_AVAILABLE:
        return {"text": "", "words": [], "avg_confidence": 0.0}

    img = Image.open(io.BytesIO(image_bytes))
    raw = pytesseract.image_to_data(img, config=_CONFIG, output_type=pytesseract.Output.DICT)

    words, confidences = [], []
    for i, word in enumerate(raw["text"]):
        conf = int(raw["conf"][i])
        if conf < 0 or not word.strip():
            continue
        x, y, w, h = raw["left"][i], raw["top"][i], raw["width"][i], raw["height"][i]
        words.append({"text": word, "bbox": [x, y, x + w, y + h], "confidence": conf / 100.0})
        confidences.append(conf)

    avg = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
    return {
        "text": " ".join(wd["text"] for wd in words),
        "words": words,
        "avg_confidence": round(avg, 4),
    }


def ocr_document(file_path: Path) -> list[dict]:
    """
    OCR every page of a PDF.
    Returns list of page dicts matching pdf_parser.extract_pages shape,
    with an extra 'avg_confidence' key per page.
    """
    import fitz
    doc = fitz.open(str(file_path))
    pages = []
    for i in range(len(doc)):
        img_bytes = render_page_image(file_path, page_index=i)
        result = _ocr_bytes(img_bytes)
        pages.append({
            "page_num": i + 1,
            "text": result["text"],
            "words": result["words"],
            "avg_confidence": result["avg_confidence"],
        })
    return pages
