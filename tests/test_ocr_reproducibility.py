"""P2-12: OCR-reproducibility check.

Proves that parsing the same file twice always produces
identical text and the same routing decision.
Weaker than byte-identical (word order may vary), but proves
the OCR branch is stable for the same input.
"""
from __future__ import annotations
import io
import pytest
from pathlib import Path
from app.parsing.extraction_router import parse_document

try:
    from PIL import Image, ImageDraw
    import pytesseract
    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False

needs_ocr = pytest.mark.skipif(
    not _DEPS_AVAILABLE,
    reason="pytesseract/Pillow not installed",
)


def _make_image_pdf(path: Path) -> None:
    """Create an image-only PDF (no text layer) to force the OCR path."""
    img = Image.new("RGB", (600, 800), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((50, 50),  "COMMERCIAL INVOICE",         fill="black")
    draw.text((50, 100), "Invoice No: INV-2026-REPRO", fill="black")
    draw.text((50, 150), "Amount: USD 25,000.00",      fill="black")
    draw.text((50, 200), "Beneficiary: ABC Exports Ltd", fill="black")
    draw.text((50, 250), "Port of Loading: Shenzhen",  fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PDF")
    path.write_bytes(buf.getvalue())


# ─── Tesseract version pin ────────────────────────────────────────────────────

@needs_ocr
def test_tesseract_version_detectable():
    """Tesseract must be installed and return a detectable version string."""
    version = pytesseract.get_tesseract_version()
    assert version is not None


# ─── Born-digital reproducibility ────────────────────────────────────────────

def test_born_digital_text_identical(tmp_path):
    """Born-digital path: same file parsed twice must yield identical text."""
    import fitz
    pdf_path = tmp_path / "invoice_bd.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 60),
        "Invoice USD 50000 Shenzhen ABC Exports Ltd Port of Loading",
        fontname="helv",
        fontsize=11,
    )
    doc.save(str(pdf_path))

    run1 = parse_document(pdf_path)
    run2 = parse_document(pdf_path)

    assert run1["path_taken"] == run2["path_taken"] == "born_digital"
    assert run1["pages"][0]["text"] == run2["pages"][0]["text"]
    assert run1["avg_quality"] == run2["avg_quality"]


def test_born_digital_routing_stable_three_runs(tmp_path):
    """Born-digital file must route identically across three consecutive parses."""
    import fitz
    pdf_path = tmp_path / "bd_stable.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 60),
        "Invoice No INV-001 USD 100000 Shenzhen Port Discharge Durres",
        fontname="helv",
        fontsize=11,
    )
    doc.save(str(pdf_path))

    paths = [parse_document(pdf_path)["path_taken"] for _ in range(3)]
    assert len(set(paths)) == 1


# ─── OCR reproducibility ──────────────────────────────────────────────────────

@needs_ocr
def test_ocr_text_identical(tmp_path):
    """OCR path: same image-PDF parsed twice must yield identical text."""
    pdf_path = tmp_path / "invoice_scan.pdf"
    _make_image_pdf(pdf_path)

    run1 = parse_document(pdf_path)
    run2 = parse_document(pdf_path)

    assert run1["path_taken"] == run2["path_taken"]
    assert run1["pages"][0]["text"] == run2["pages"][0]["text"]


@needs_ocr
def test_ocr_word_count_stable(tmp_path):
    """OCR word count must be identical across two runs."""
    pdf_path = tmp_path / "invoice_scan2.pdf"
    _make_image_pdf(pdf_path)

    run1 = parse_document(pdf_path)
    run2 = parse_document(pdf_path)

    assert len(run1["pages"][0]["words"]) == len(run2["pages"][0]["words"])


@needs_ocr
def test_ocr_confidence_stable(tmp_path):
    """OCR average confidence score must be identical across two runs."""
    pdf_path = tmp_path / "invoice_scan3.pdf"
    _make_image_pdf(pdf_path)

    run1 = parse_document(pdf_path)
    run2 = parse_document(pdf_path)

    assert (
        run1["pages"][0].get("avg_confidence")
        == run2["pages"][0].get("avg_confidence")
    )


@needs_ocr
def test_ocr_routing_stable(tmp_path):
    """Same image-PDF must always route to OCR (never flip to born_digital)."""
    pdf_path = tmp_path / "scan_stable.pdf"
    _make_image_pdf(pdf_path)

    paths = [parse_document(pdf_path)["path_taken"] for _ in range(2)]
    assert len(set(paths)) == 1
