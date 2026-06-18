"""P2-11 (partial): Agent B + D validation against P2-generated scenario bundles.

Scenario 1 (scenario_01): Clean bundle — all documents consistent, no discrepancies.
    Agent D must return overall_status='CLEAN' with no major/minor comparisons failing.

Scenario 2 (scenario_02): B/L on-board date (15/07/2026) is after latest shipment
    date (2026-07-10) — CHK-06 must flag this as a MAJOR discrepancy.

Scenario 9 (scenario_09): Clean sight L/C — same extraction/matching expectations
    as scenario_01 (honour path).

Scenarios 4, 6, 7 (P3-owned): stubs here, skipped until P3 creates the bundles
    and the full pipeline (Agents C + E + H) is in develop.
"""
from __future__ import annotations
import pytest
from pathlib import Path

from app.agents import agent_a_intake, agent_b_extraction, agent_d_matching
from app.state import PipelineState
from app.schemas.common import Severity

BUNDLES_DIR = Path("tests/bundles")
SCENARIO_01 = BUNDLES_DIR / "scenario_01"
SCENARIO_02 = BUNDLES_DIR / "scenario_02"
SCENARIO_04 = BUNDLES_DIR / "scenario_04"
SCENARIO_06 = BUNDLES_DIR / "scenario_06"
SCENARIO_07 = BUNDLES_DIR / "scenario_07"
SCENARIO_09 = BUNDLES_DIR / "scenario_09"


def _run_abd(bundle_dir: Path, tmp_path: Path) -> PipelineState:
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


# ── Scenario 1: clean bundle → no discrepancies ───────────────────────────────

def test_s01_bundles_present():
    assert SCENARIO_01.exists(), f"Bundle not found: {SCENARIO_01}"
    assert len(list(SCENARIO_01.glob("*.pdf"))) >= 3


def test_s01_overall_status_clean(tmp_path):
    """Clean bundle must produce overall_status='CLEAN' from Agent D."""
    state = _run_abd(SCENARIO_01, tmp_path)
    assert state.match_result is not None, "Agent D produced no MatchResult"
    assert state.match_result.overall_status == "CLEAN", (
        f"Expected CLEAN on clean bundle, got {state.match_result.overall_status!r}. "
        f"Failing comparisons: "
        f"{[(c.field_name, c.severity, c.notes) for c in state.match_result.comparisons if not c.match]}"
    )


def test_s01_no_major_discrepancies(tmp_path):
    """Clean bundle must have zero MAJOR severity failing comparisons."""
    state = _run_abd(SCENARIO_01, tmp_path)
    assert state.match_result is not None
    majors = [
        c for c in state.match_result.comparisons
        if c.severity == Severity.major and not c.match
    ]
    assert len(majors) == 0, f"Unexpected majors on clean bundle: {majors}"


def test_s01_extraction_non_empty(tmp_path):
    """Agent B must extract at least one field from the clean bundle."""
    state = _run_abd(SCENARIO_01, tmp_path)
    assert state.extracted is not None
    total_fields = sum(len(d.fields) for d in state.extracted.documents)
    assert total_fields > 0, "Agent B extracted 0 fields from a clean born-digital bundle"


# ── Scenario 2: bl_late → CHK-06 MAJOR discrepancy ───────────────────────────

def test_s02_bundles_present():
    assert SCENARIO_02.exists(), f"Bundle not found: {SCENARIO_02}"
    assert len(list(SCENARIO_02.glob("*.pdf"))) >= 3


def test_s02_chk06_fails_on_late_bl(tmp_path):
    """CHK-06: on_board_date (15/07) is after latest_shipment_date (10/07) — must be MAJOR."""
    state = _run_abd(SCENARIO_02, tmp_path)
    assert state.match_result is not None, "Agent D produced no MatchResult"
    chk06 = next(
        (c for c in state.match_result.comparisons
         if c.field_name == "on_board_date_vs_latest_shipment"),
        None,
    )
    assert chk06 is not None, "CHK-06 (on_board_date_vs_latest_shipment) not found in MatchResult"
    assert chk06.match is False, (
        f"Expected CHK-06 to FAIL for late B/L but match=True. "
        f"values={[(v.document, v.value) for v in chk06.values]}"
    )
    assert chk06.severity == Severity.major, (
        f"Expected severity=major for late B/L, got {chk06.severity}"
    )


def test_s02_overall_status_major_discrepancy(tmp_path):
    """Late B/L bundle must produce overall_status='MAJOR_DISCREPANCY'."""
    state = _run_abd(SCENARIO_02, tmp_path)
    assert state.match_result is not None
    assert state.match_result.overall_status == "MAJOR_DISCREPANCY", (
        f"Expected MAJOR_DISCREPANCY, got {state.match_result.overall_status!r}"
    )


def test_s02_on_board_date_extracted(tmp_path):
    """Agent B must extract the on_board_date from the B/L in the late scenario."""
    state = _run_abd(SCENARIO_02, tmp_path)
    assert state.match_result is not None
    chk06 = next(
        (c for c in state.match_result.comparisons
         if c.field_name == "on_board_date_vs_latest_shipment"),
        None,
    )
    assert chk06 is not None
    bol_val = next((v for v in chk06.values if v.document == "bill_of_lading"), None)
    assert bol_val is not None, "on_board_date not extracted from bill_of_lading"
    assert "15" in bol_val.value or "07" in bol_val.value, (
        f"Unexpected on_board_date value: {bol_val.value!r}"
    )


# ── Scenario 9: clean sight L/C → no discrepancies ───────────────────────────

def test_s09_bundles_present():
    assert SCENARIO_09.exists(), f"Bundle not found: {SCENARIO_09}"
    assert len(list(SCENARIO_09.glob("*.pdf"))) >= 3


def test_s09_overall_status_clean(tmp_path):
    """Clean sight L/C must also produce overall_status='CLEAN'."""
    state = _run_abd(SCENARIO_09, tmp_path)
    assert state.match_result is not None
    assert state.match_result.overall_status == "CLEAN", (
        f"Expected CLEAN on sight LC bundle, got {state.match_result.overall_status!r}"
    )


# ── Scenario 4, 6, 7: P3-owned bundles — stubs until P3 creates them ─────────

@pytest.mark.skip(reason="Scenario 04 bundle not yet created — P3 owns partial-shipment check")
def test_s04_partial_shipment_prohibited(tmp_path):
    """CHK via Agent C (P3): partial shipment flag on manifest must trigger discrepancy."""
    state = _run_abd(SCENARIO_04, tmp_path)
    assert state.match_result is not None


@pytest.mark.skip(reason="Scenario 06 bundle not yet created — P3 owns sanctions screening")
def test_s06_sanctions_hit_vessel_flag(tmp_path):
    """Agent E (P3): vessel flag-state sanctions hit must freeze the pipeline."""
    state = _run_abd(SCENARIO_06, tmp_path)
    assert state.match_result is not None


@pytest.mark.skip(reason="Scenario 07 bundle not yet created — P3 owns 21-day late-presentation rule")
def test_s07_late_presentation_21_day(tmp_path):
    """Agent C (P3): presentation beyond 21 days after B/L must produce REFER/REFUSE."""
    state = _run_abd(SCENARIO_07, tmp_path)
    assert state.match_result is not None
