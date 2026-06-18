"""Tests for extraction_router: born-digital vs OCR routing."""
import pytest
from pathlib import Path
from app.parsing.quality_scorer import score_page, score_document
from app.parsing.extraction_router import parse_document


# ─── quality_scorer ───────────────────────────────────────────────────────────

def test_score_page_blank():
    assert score_page("") == pytest.approx(0.0)


def test_score_page_rich_text():
    text = "Invoice No: INV-2026-001\nTotal Amount: USD 250,000.00\nBeneficiary: ABC Ltd" * 3
    score = score_page(text)
    assert score > 0.6


def test_score_page_gibberish():
    score = score_page("!!@@##$$%%^^&&**((")
    assert score < 0.5


def test_score_document_born_digital():
    pages = [{"text": "Invoice No: INV-2026-001  Amount: USD 250,000.00  Beneficiary: ABC Ltd" * 4}]
    decision, avg = score_document(pages)
    assert decision == "born_digital"
    assert avg >= 0.4


def test_score_document_empty():
    decision, avg = score_document([])
    assert decision == "scan"
    assert avg == 0.0


def test_score_document_blank_pages():
    pages = [{"text": ""}, {"text": "   "}]
    decision, avg = score_document(pages)
    assert decision == "scan"


# ─── extraction_router ───────────────────────────────────────────────────────

def test_parse_document_missing_file():
    result = parse_document(Path("/nonexistent/path/file.pdf"))
    assert result["pages"] == []
    assert result["error"] is not None


def test_parse_document_born_digital(tmp_path):
    """A born-digital PDF should route via PyMuPDF, not OCR."""
    import fitz
    pdf_path = tmp_path / "invoice.pdf"
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "Invoice No: INV-2026-001\n"
        "Total Amount: USD 250,000.00\n"
        "Beneficiary: ABC Exports Ltd\n"
        "Applicant: XYZ Imports Inc\n"
        "Port of Loading: Shenzhen\n"
        "Port of Discharge: Durres\n"
    )
    page.insert_text((50, 60), text, fontname="helv", fontsize=11)
    doc.save(str(pdf_path))

    result = parse_document(pdf_path)

    assert result["error"] is None
    assert result["path_taken"] == "born_digital"
    assert len(result["pages"]) == 1
    assert "Invoice" in result["pages"][0]["text"]


def test_parse_document_pages_have_words(tmp_path):
    """Each page dict must expose a 'words' list."""
    import fitz
    pdf_path = tmp_path / "doc.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 60), "Hello World Invoice USD 1000", fontname="helv", fontsize=11)
    doc.save(str(pdf_path))

    result = parse_document(pdf_path)
    assert "words" in result["pages"][0]
    assert len(result["pages"][0]["words"]) > 0


def test_parse_document_tagged_path(tmp_path):
    """path_taken must be either 'born_digital' or 'ocr'."""
    import fitz
    pdf_path = tmp_path / "doc.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 60), "Some invoice content USD 5000", fontname="helv", fontsize=11)
    doc.save(str(pdf_path))

    result = parse_document(pdf_path)
    assert result["path_taken"] in ("born_digital", "ocr")
