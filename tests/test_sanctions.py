"""Tests for Agent E — sanctions screening engine."""
from app.rules.sanctions_lists import screen
from app.schemas.common import RiskLevel
from app.tools.policy_loader import load_policy
from tests.fixtures.p3_sample import sample_context, sample_context_sanctioned


def _policy():
    return load_policy()


# ─── Clean scenario ──────────────────────────────────────────────────────────

def test_clean_bundle_clears():
    result = screen(sample_context(), _policy())
    assert result.overall_status == "CLEAR"
    assert result.freeze_processing is False
    assert result.risk_level == RiskLevel.low


def test_clean_bundle_has_no_hits():
    result = screen(sample_context(), _policy())
    assert len(result.hits) == 0


def test_clean_bundle_screens_all_entities():
    result = screen(sample_context(), _policy())
    assert result.entities_screened == 5


# ─── Sanctioned scenario ─────────────────────────────────────────────────────

def test_sanctioned_bundle_freezes():
    result = screen(sample_context_sanctioned(), _policy())
    assert result.overall_status == "FREEZE"
    assert result.freeze_processing is True
    assert result.risk_level == RiskLevel.critical


def test_sanctioned_bundle_flags_embargoed_country():
    result = screen(sample_context_sanctioned(), _policy())
    assert "Iran" in result.countries_flagged


def test_sanctioned_bundle_catches_vessel_and_beneficiary():
    result = screen(sample_context_sanctioned(), _policy())
    names = {h.entity_name for h in result.hits}
    assert "MV Crimson Star" in names
    assert "Crimson Star Shipping Ltd" in names


def test_sanctioned_hits_have_evidence_fields():
    result = screen(sample_context_sanctioned(), _policy())
    for h in result.hits:
        assert h.list_name in ("OFAC", "EU", "UN")
        assert 0.0 <= h.match_score <= 1.0
        assert h.match_type in ("exact", "fuzzy")
        assert h.recommended_action in ("FREEZE", "MANUAL_REVIEW")


def test_actionable_hits_drive_freeze():
    result = screen(sample_context_sanctioned(), _policy())
    actionable = [h for h in result.hits if not h.is_false_positive]
    assert len(actionable) >= 1


# ─── Determinism ─────────────────────────────────────────────────────────────

def test_sanctions_screen_is_deterministic():
    p = _policy()
    a = screen(sample_context_sanctioned(), p).model_dump_json()
    b = screen(sample_context_sanctioned(), p).model_dump_json()
    assert a == b
