"""P2-11: Agent B + D validation against P2-owned scenario bundles.

Scenario 3 (scenario_03): Invoice 0.3 % above L/C amount — must pass CHK-05
    within the default 5 % tolerance.  Proves calculator_tool + matching_rules
    handle tolerance correctly.

Scenario 4 (scenario_04): Partial shipment presented but L/C prohibits it —
    UCP 600 Art 31 (UCP600-31-partial) must fail and final decision must be REFUSE.

Scenario 5 (scenario_05): Beneficiary name differs slightly ("Company Ltd" vs
    "Co Ltd") — CHK-08 must score >= 0.85 and return match=True.  Proves
    fuzzy_match_tool handles common abbreviation variations.

Scenario 6 (scenario_06): Vessel on OFAC SDN list — sanctions screening must
    produce a HIT and freeze processing (final decision REFUSE with sanctions_hits > 0).

Scenario 7 (scenario_07): Documents presented 55 days after shipment — UCP 600
    Art 14(c) (UCP600-14c-presentation) must fail and final decision must be REFUSE.

Scenario 8 (scenario_08): Scanned (image-only) bundle — PDF must be recognised
    as scan-quality by quality_scorer, and Agent B must flag low-confidence
    fields.  OCR routing asserted only when Tesseract is available.
"""
from __future__ import annotations
import pytest
from pathlib import Path

from app.agents import agent_a_intake, agent_b_extraction, agent_d_matching
from app.pipeline import run_pipeline
from app.state import PipelineState
from app.schemas.common import Severity

BUNDLES_DIR = Path("tests/bundles")
SCENARIO_03 = BUNDLES_DIR / "scenario_03"
SCENARIO_04 = BUNDLES_DIR / "scenario_04"
SCENARIO_05 = BUNDLES_DIR / "scenario_05"
SCENARIO_06 = BUNDLES_DIR / "scenario_06"
SCENARIO_07 = BUNDLES_DIR / "scenario_07"
SCENARIO_08 = BUNDLES_DIR / "scenario_08"


def _run_full(bundle_dir: Path, tmp_path: Path) -> PipelineState:
    """Run the full pipeline A→B→C→D→E→H and return the resulting state."""
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    state = PipelineState(
        bundle_id=bundle_dir.name,
        bundle_path=bundle_dir,
        run_dir=run_dir,
    )
    return run_pipeline(state)


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


# ── Scenario 4: partial shipment prohibited → UCP 600 Art 31 → REFUSE ─────────

def test_s04_bundles_present():
    """Scenario 04 bundle directory and PDFs must exist."""
    assert SCENARIO_04.exists(), f"Bundle not found: {SCENARIO_04}"
    assert len(list(SCENARIO_04.glob("*.pdf"))) >= 3


def test_s04_final_decision_refuse(tmp_path):
    """Pipeline must REFUSE when partial shipment is presented but L/C prohibits it."""
    state = _run_full(SCENARIO_04, tmp_path)
    assert state.final_decision is not None, "Pipeline produced no final decision"
    assert state.final_decision.decision == "REFUSE", (
        f"Expected REFUSE for partial-shipment scenario, got {state.final_decision.decision!r}. "
        f"Basis: {state.final_decision.decision_basis!r}"
    )


def test_s04_ucp31_partial_shipment_fails(tmp_path):
    """UCP600-31-partial rule must fail when B/L declares partial shipment."""
    state = _run_full(SCENARIO_04, tmp_path)
    assert state.ucp_result is not None, "UCP result missing"
    rule = next(
        (r for r in state.ucp_result.results if r.rule_id == "UCP600-31-partial"),
        None,
    )
    assert rule is not None, "UCP600-31-partial rule not found in results"
    assert rule.passed is False, (
        "Expected UCP600-31-partial to FAIL for partial-shipment bundle, but passed=True"
    )


def test_s04_no_sanctions_hit(tmp_path):
    """Partial-shipment scenario must not trigger any sanctions hits."""
    state = _run_full(SCENARIO_04, tmp_path)
    assert state.sanctions is not None
    assert state.sanctions.overall_status != "FREEZE", (
        "Unexpected FREEZE on partial-shipment scenario — check OFAC list"
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


# ── Scenario 6: vessel on OFAC SDN → sanctions freeze → REFUSE ────────────────

def test_s06_bundles_present():
    """Scenario 06 bundle directory and PDFs must exist."""
    assert SCENARIO_06.exists(), f"Bundle not found: {SCENARIO_06}"
    assert len(list(SCENARIO_06.glob("*.pdf"))) >= 3


def test_s06_final_decision_refuse_with_sanctions(tmp_path):
    """Pipeline must REFUSE and sanctions_hits > 0 when vessel is on OFAC SDN list."""
    state = _run_full(SCENARIO_06, tmp_path)
    assert state.final_decision is not None, "Pipeline produced no final decision"
    assert state.final_decision.decision == "REFUSE", (
        f"Expected REFUSE for sanctions-hit scenario, got {state.final_decision.decision!r}. "
        f"Basis: {state.final_decision.decision_basis!r}"
    )
    assert state.final_decision.findings_summary.sanctions_hits > 0, (
        "Expected sanctions_hits > 0 in findings_summary for OFAC vessel hit"
    )


def test_s06_sanctions_freeze_triggered(tmp_path):
    """Agent E must set freeze_processing=True for the sanctioned vessel."""
    state = _run_full(SCENARIO_06, tmp_path)
    assert state.sanctions is not None, "Sanctions result missing"
    assert state.sanctions.freeze_processing is True, (
        f"Expected freeze_processing=True for OFAC hit, got status={state.sanctions.overall_status!r}"
    )
    vessel_hits = [h for h in state.sanctions.hits if h.entity_type == "vessel"]
    assert len(vessel_hits) > 0, (
        f"Expected a vessel sanctions hit, but got: {[(h.entity_name, h.entity_type) for h in state.sanctions.hits]}"
    )


# ── Scenario 7: late presentation > 21 days → UCP 600 Art 14(c) → REFUSE ─────

def test_s07_bundles_present():
    """Scenario 07 bundle directory and PDFs must exist."""
    assert SCENARIO_07.exists(), f"Bundle not found: {SCENARIO_07}"
    assert len(list(SCENARIO_07.glob("*.pdf"))) >= 3


def test_s07_final_decision_refuse(tmp_path):
    """Pipeline must REFUSE when presentation period exceeds the 21-day L/C rule."""
    state = _run_full(SCENARIO_07, tmp_path)
    assert state.final_decision is not None, "Pipeline produced no final decision"
    assert state.final_decision.decision == "REFUSE", (
        f"Expected REFUSE for late-presentation scenario, got {state.final_decision.decision!r}. "
        f"Basis: {state.final_decision.decision_basis!r}"
    )


def test_s07_ucp14c_presentation_fails(tmp_path):
    """UCP600-14c-presentation rule must fail when presentation is 55 days after shipment."""
    state = _run_full(SCENARIO_07, tmp_path)
    assert state.ucp_result is not None, "UCP result missing"
    rule = next(
        (r for r in state.ucp_result.results if r.rule_id == "UCP600-14c-presentation"),
        None,
    )
    assert rule is not None, "UCP600-14c-presentation rule not found in results"
    assert rule.passed is False, (
        "Expected UCP600-14c-presentation to FAIL for late-presentation bundle, but passed=True"
    )


def test_s07_no_sanctions_hit(tmp_path):
    """Late-presentation scenario must not trigger any sanctions hits."""
    state = _run_full(SCENARIO_07, tmp_path)
    assert state.sanctions is not None
    assert state.sanctions.overall_status != "FREEZE", (
        "Unexpected FREEZE on late-presentation scenario — check OFAC list"
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
