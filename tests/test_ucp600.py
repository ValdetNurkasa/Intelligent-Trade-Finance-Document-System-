"""Tests for Agent C — UCP 600 compliance rule engine."""
from app.rules.ucp600 import (
    run_ucp_checks,
    check_expiry,
    check_latest_shipment,
    check_presentation_period,
    check_partial_shipment,
    check_transhipment,
)
from app.schemas.common import Severity
from tests.fixtures.p3_sample import sample_context, sample_extracted


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _rule(result, rule_id_part: str):
    for r in result.results:
        if rule_id_part in r.rule_id:
            return r
    return None


# ─── Full-run behaviour ──────────────────────────────────────────────────────

def test_run_returns_ucp_result_for_bundle():
    result = run_ucp_checks(sample_context(), sample_extracted())
    assert result.bundle_id == "bundle_002_bl_expiry"
    assert result.rules_checked == len(result.results)
    assert result.rules_passed + result.rules_failed == result.rules_checked


def test_bl_after_expiry_bundle_is_non_compliant():
    result = run_ucp_checks(sample_context(), sample_extracted())
    assert result.overall_compliant is False
    assert result.rules_failed >= 1


def test_every_result_has_a_finding_with_evidence():
    result = run_ucp_checks(sample_context(), sample_extracted())
    for r in result.results:
        assert r.finding is not None
        assert r.finding.evidence is not None
        assert r.finding.source_agent == "agent_c"


# ─── Expiry rule ─────────────────────────────────────────────────────────────

def test_expiry_fails_when_shipment_after_expiry():
    r = check_expiry(sample_context(), sample_extracted(), "agent_c")
    assert r.passed is False
    assert r.severity == Severity.major


def test_expiry_passes_when_shipment_before_expiry():
    ctx = sample_context()
    ctx.expiry_date = "2026-12-31"
    r = check_expiry(ctx, sample_extracted(), "agent_c")
    assert r.passed is True


# ─── Latest shipment rule ────────────────────────────────────────────────────

def test_latest_shipment_fails_when_late():
    r = check_latest_shipment(sample_context(), sample_extracted(), "agent_c")
    assert r.passed is False
    assert r.severity == Severity.major


def test_latest_shipment_passes_when_no_latest_date():
    ctx = sample_context()
    ctx.latest_shipment_date = None
    r = check_latest_shipment(ctx, sample_extracted(), "agent_c")
    assert r.passed is True


# ─── Presentation period (21-day rule) ───────────────────────────────────────

def test_presentation_fails_when_after_expiry():
    r = check_presentation_period(sample_context(), sample_extracted(), "agent_c")
    assert r.passed is False
    assert r.severity == Severity.major


# ─── Partial shipment rule ───────────────────────────────────────────────────

def test_partial_shipment_passes_when_not_present():
    r = check_partial_shipment(sample_context(), sample_extracted(), "agent_c")
    assert r.passed is True


def test_partial_shipment_fails_when_prohibited_but_present():
    ctx = sample_context()
    ext = sample_extracted()
    for doc in ext.documents:
        if doc.document_type.value == "bill_of_lading":
            for f in doc.fields:
                if f.field_name == "partial_shipment":
                    f.value = "true"
    r = check_partial_shipment(ctx, ext, "agent_c")
    assert r.passed is False
    assert r.severity == Severity.major


def test_partial_shipment_passes_when_allowed():
    ctx = sample_context()
    ctx.flags.partial_shipment_allowed = True
    ext = sample_extracted()
    for doc in ext.documents:
        if doc.document_type.value == "bill_of_lading":
            for f in doc.fields:
                if f.field_name == "partial_shipment":
                    f.value = "true"
    r = check_partial_shipment(ctx, ext, "agent_c")
    assert r.passed is True


# ─── Transhipment rule ───────────────────────────────────────────────────────

def test_transhipment_fails_when_prohibited_but_present():
    ctx = sample_context()
    ext = sample_extracted()
    for doc in ext.documents:
        if doc.document_type.value == "bill_of_lading":
            for f in doc.fields:
                if f.field_name == "transhipment":
                    f.value = "true"
    r = check_transhipment(ctx, ext, "agent_c")
    assert r.passed is False


def test_transhipment_passes_when_allowed():
    ctx = sample_context()
    ctx.flags.transhipment_allowed = True
    ext = sample_extracted()
    for doc in ext.documents:
        if doc.document_type.value == "bill_of_lading":
            for f in doc.fields:
                if f.field_name == "transhipment":
                    f.value = "true"
    r = check_transhipment(ctx, ext, "agent_c")
    assert r.passed is True


# ─── Determinism ─────────────────────────────────────────────────────────────

def test_ucp_result_is_deterministic():
    a = run_ucp_checks(sample_context(), sample_extracted()).model_dump_json()
    b = run_ucp_checks(sample_context(), sample_extracted()).model_dump_json()
    assert a == b
