"""P2-11: Agent B + D validation against P2-owned scenario bundles.

Scenario 3 (scenario_03): Invoice 0.3 % above L/C amount — must pass CHK-05
    within the default 5 % tolerance.  Proves calculator_tool + matching_rules
    handle tolerance correctly.

Scenario 5 (scenario_05): Beneficiary name differs slightly ("Company Ltd" vs
    "Co Ltd") — CHK-08 must score >= 0.85 and return match=True.  Proves
    fuzzy_match_tool handles common abbreviation variations.

Scenario 8 (scenario_08): Scanned (image-only) bundle — PDF must be recognised
    as scan-quality by quality_scorer, and Agent B must flag low-confidence
    fields.  OCR routing asserted only when Tesseract is available.
"""
from __future__ import annotations
import pytest
from pathlib import Path

from app.agents import agent_a_intake, agent_b_extraction, agent_d_matching
from app.state import PipelineState
from app.schemas.common import Severity

BUNDLES_DIR = Path("tests/bundles")
SCENARIO_03 = BUNDLES_DIR / "scenario_03"
SCENARIO_05 = BUNDLES_DIR / "scenario_05"
SCENARIO_08 = BUNDLES_DIR / "scenario_08"


def _run_abd(bundle_dir: Path, tmp_path: Path) -> PipelineState:
    """Run Agent A → B → D against a bundle and return the resulting state."""
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    state = PipelineState(
        bundle_id=bundle_dir.name,
        bundle_path=bundle_dir,
        run_dir=run_dir,
    )
    state = agent_a_intake.run(state)
    state = agent_b_extraction.run(state)
    state = agent_d_matching.run(state)
    return state


# ── Scenario 3: invoice 0.3 % over L/C, passes 5 % tolerance ─────────────────

def test_s03_bundles_present():
    """Scenario 03 bundle directory and PDFs must exist."""
    assert SCENARIO_03.exists(), f"Bundle not found: {SCENARIO_03}"
    pdfs = list(SCENARIO_03.glob("*.pdf"))
    assert len(pdfs) >= 3, f"Expected at least 3 PDFs, found {len(pdfs)}"


def test_s03_amount_within_tolerance(tmp_path):
    """CHK-05: invoice 250,750 is 0.3 % over LC 250,000 — within 5 % tolerance."""
    state = _run_abd(SCENARIO_03, tmp_path)
    assert state.match_result is not None, "Agent D produced no MatchResult"
    chk05 = next(
        (c for c in state.match_result.comparisons if c.field_name == "amount"),
        None,
    )
    assert chk05 is not None, "CHK-05 (amount) comparison not found in MatchResult"
    assert chk05.match is True, (
        f"Expected amount within 5 % tolerance but match=False: {chk05.notes}  "
        f"values={[(v.document, v.value) for v in chk05.values]}"
    )


def test_s03_no_major_amount_discrepancy(tmp_path):
    """Tolerance bundle must not produce a MAJOR severity on the amount check."""
    state = _run_abd(SCENARIO_03, tmp_path)
    assert state.match_result is not None
    amount_majors = [
        c for c in state.match_result.comparisons
        if c.field_name == "amount" and c.severity == Severity.major
    ]
    assert len(amount_majors) == 0, (
        f"Unexpected MAJOR on amount comparison: {amount_majors}"
    )


def test_s03_correct_values_extracted(tmp_path):
    """Agent B must extract invoice amount=250,750 and LC amount=250,000."""
    state = _run_abd(SCENARIO_03, tmp_path)
    assert state.match_result is not None
    chk05 = next(
        (c for c in state.match_result.comparisons if c.field_name == "amount"),
        None,
    )
    assert chk05 is not None
    values = {v.document: v.value for v in chk05.values}
    assert "commercial_invoice" in values, "Invoice amount not extracted"
    assert "250,750" in values["commercial_invoice"], (
        f"Expected invoice amount ~250,750, got {values['commercial_invoice']}"
    )


# ── Scenario 5: beneficiary name variation → fuzzy match ──────────────────────

def test_s05_bundles_present():
    """Scenario 05 bundle directory and PDFs must exist."""
    assert SCENARIO_05.exists(), f"Bundle not found: {SCENARIO_05}"
    pdfs = list(SCENARIO_05.glob("*.pdf"))
    assert len(pdfs) >= 3, f"Expected at least 3 PDFs, found {len(pdfs)}"


def test_s05_beneficiary_fuzzy_match(tmp_path):
    """CHK-08: 'Shenzhen Lition Electronics Company Ltd' vs 'Co Ltd' must match."""
    state = _run_abd(SCENARIO_05, tmp_path)
    assert state.match_result is not None, "Agent D produced no MatchResult"
    chk08 = next(
        (c for c in state.match_result.comparisons if c.field_name == "beneficiary_name"),
        None,
    )
    assert chk08 is not None, "CHK-08 (beneficiary_name) comparison not found"
    assert chk08.match is True, (
        f"Expected fuzzy match for name variation but match=False "
        f"(score={chk08.match_score}): {chk08.notes}  "
        f"values={[(v.document, v.value) for v in chk08.values]}"
    )


def test_s05_fuzzy_score_above_threshold(tmp_path):
    """CHK-08 match score must be >= 0.85 (project THRESHOLD)."""
    state = _run_abd(SCENARIO_05, tmp_path)
    assert state.match_result is not None
    chk08 = next(
        (c for c in state.match_result.comparisons if c.field_name == "beneficiary_name"),
        None,
    )
    assert chk08 is not None
    assert chk08.match_score >= 0.85, (
        f"Match score {chk08.match_score:.4f} is below 0.85 threshold"
    )


def test_s05_both_names_extracted(tmp_path):
    """Agent B must extract beneficiary names from both invoice and L/C."""
    state = _run_abd(SCENARIO_05, tmp_path)
    assert state.match_result is not None
    chk08 = next(
        (c for c in state.match_result.comparisons if c.field_name == "beneficiary_name"),
        None,
    )
    assert chk08 is not None
    assert len(chk08.values) == 2, (
        f"Expected 2 values (invoice + LC) for CHK-08, got {len(chk08.values)}"
    )


# ── Scenario 8: scanned bundle → low quality / low confidence ─────────────────

try:
    import pytesseract as _pt
    _pt.get_tesseract_version()  # raises if binary not in PATH
    _TESSERACT_AVAILABLE = True
except Exception:
    _TESSERACT_AVAILABLE = False

needs_tesseract = pytest.mark.skipif(
    not _TESSERACT_AVAILABLE,
    reason="pytesseract not installed — OCR path skipped",
)


def test_s08_bundles_present():
    """Scenario 08 (scanned) bundle directory and PDFs must exist."""
    assert SCENARIO_08.exists(), f"Bundle not found: {SCENARIO_08}"
    pdfs = list(SCENARIO_08.glob("*.pdf"))
    assert len(pdfs) >= 3, f"Expected at least 3 PDFs, found {len(pdfs)}"


def test_s08_scanned_quality_below_cutoff():
    """Scanned PDFs must have avg_quality < 0.4 (the born-digital cutoff)."""
    from app.parsing.pdf_parser import extract_pages
    from app.parsing.quality_scorer import score_document

    pdf = SCENARIO_08 / "invoice.pdf"
    pages = extract_pages(pdf)
    decision, avg_quality = score_document(pages)
    assert avg_quality < 0.4, (
        f"Scanned PDF quality {avg_quality:.3f} is unexpectedly high; "
        "image-only PDF should have quality=0.0"
    )
    assert decision == "scan", f"Expected decision='scan', got '{decision}'"


def test_s08_agent_b_signals_extraction_failure(tmp_path):
    """Agent B must signal that scanned docs could not be extracted (no OCR available).

    When Tesseract binary is absent, extraction_router returns an error and agent_b
    records a warning and produces 0 fields — which is the pipeline's signal that
    manual review is required for these documents.
    """
    state = _run_abd(SCENARIO_08, tmp_path)
    assert state.extracted is not None, "Agent B produced no ExtractedDocs"

    if _TESSERACT_AVAILABLE:
        # With OCR available, fields are either low-confidence (USE_LLM=false)
        # or llm_derived (USE_LLM=true retried them) — both prove OCR penalty fired
        flagged = [
            f
            for doc in state.extracted.documents
            for f in doc.fields
            if f.low_confidence or f.llm_derived
        ]
        assert len(flagged) > 0, (
            "Expected low-confidence or llm_derived fields when OCR path taken on scanned PDF"
        )
    else:
        # Without OCR binary: agent_b falls back to empty fields + warning
        ocr_warnings = [w for w in state.warnings if "tesseract" in w.lower() or "fallback" in w.lower()]
        empty_docs = [d for d in state.extracted.documents if len(d.fields) == 0]
        assert len(ocr_warnings) > 0 or len(empty_docs) > 0, (
            "Expected OCR failure warnings or empty docs on scanned bundle without Tesseract"
        )


@needs_tesseract
def test_s08_routes_to_ocr():
    """With Tesseract available, scanned PDF must route through OCR path."""
    from app.parsing.extraction_router import parse_document

    pdf = SCENARIO_08 / "invoice.pdf"
    result = parse_document(pdf)
    assert result["path_taken"] == "ocr", (
        f"Expected path_taken='ocr' for scanned PDF, got '{result['path_taken']}'"
    )
