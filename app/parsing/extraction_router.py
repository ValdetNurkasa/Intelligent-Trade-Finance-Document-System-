from __future__ import annotations
from pathlib import Path

from app.parsing import pdf_parser, quality_scorer, ocr_parser

DEFAULT_CUTOFF = 0.4


def parse_document(file_path: Path, quality_cutoff: float = DEFAULT_CUTOFF) -> dict:
    """
    Parse one document file via the appropriate path.

    Flow:
      1. PyMuPDF extracts text + word bboxes.
      2. quality_scorer decides 'born_digital' or 'scan'.
      3. If quality < cutoff → fall back to Tesseract OCR.

    Returns:
      {
        "pages": list[dict],          # page_num, text, words (uniform shape)
        "path_taken": "born_digital" | "ocr",
        "avg_quality": float,
        "error": str | None,
      }
    """
    if not file_path.exists():
        return {"pages": [], "path_taken": "born_digital", "avg_quality": 0.0,
                "error": f"file not found: {file_path}"}

    try:
        pages = pdf_parser.extract_pages(file_path)
    except Exception as exc:
        return {"pages": [], "path_taken": "born_digital", "avg_quality": 0.0, "error": str(exc)}

    decision, avg_quality = quality_scorer.score_document(pages, cutoff=quality_cutoff)

    if decision == "born_digital":
        return {"pages": pages, "path_taken": "born_digital", "avg_quality": avg_quality, "error": None}

    try:
        ocr_pages = ocr_parser.ocr_document(file_path)
        _, ocr_quality = quality_scorer.score_document(ocr_pages)
        return {"pages": ocr_pages, "path_taken": "ocr", "avg_quality": ocr_quality, "error": None}
    except Exception as exc:
        # OCR failed — return born-digital text with a warning
        return {"pages": pages, "path_taken": "born_digital", "avg_quality": avg_quality, "error": str(exc)}
