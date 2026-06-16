"""Tests for Agent D matching rules."""
import pytest
from app.rules.matching_rules import run_matching
from app.schemas.common import DocumentType
from app.schemas.extraction import ExtractedDocs, ExtractedDocument, ExtractedField
from tests.fixtures.p2_sample import (
    sample_extracted_clean,
    sample_extracted_amount_over,
    sample_extracted_name_variation,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _result(extracted: ExtractedDocs, tolerance: float = 5.0):
    return run_matching(extracted, tolerance_pct=tolerance)


def _check(result, field_name: str):
    for c in result.comparisons:
        if c.field_name == field_name:
            return c
    return None


# ─── Clean scenario ───────────────────────────────────────────────────────────

def test_clean_presentation_is_clean():
    result = _result(sample_extracted_clean())
    assert result.overall_status == "CLEAN"


def test_clean_goods_description_matches():
    result = _result(sample_extracted_clean())
    chk = _check(result, "goods_description")
    assert chk is not None
    assert chk.match is True


def test_clean_amount_within_tolerance():
    result = _result(sample_extracted_clean(), tolerance=5.0)
    chk = _check(result, "amount")
    assert chk is not None
    assert chk.match is True


def test_clean_ports_match():
    result = _result(sample_extracted_clean())
    chk = _check(result, "port_of_loading")
    assert chk is not None
    assert chk.match is True


# ─── Amount discrepancy ───────────────────────────────────────────────────────

def test_amount_over_tight_tolerance_is_major():
    result = _result(sample_extracted_amount_over(), tolerance=0.3)
    chk = _check(result, "amount")
    assert chk is not None
    assert chk.match is False
    assert result.overall_status == "MAJOR_DISCREPANCY"


def test_amount_over_generous_tolerance_is_clean():
    result = _result(sample_extracted_amount_over(), tolerance=5.0)
    chk = _check(result, "amount")
    assert chk.match is True


# ─── Beneficiary name variation ───────────────────────────────────────────────

def test_beneficiary_name_variation_fuzzy_match():
    """Slight name variation should still pass fuzzy matching."""
    result = _result(sample_extracted_name_variation())
    chk = _check(result, "beneficiary_name")
    assert chk is not None
    assert chk.match is True


# ─── Date checks ──────────────────────────────────────────────────────────────

def test_bl_date_before_latest_shipment_passes():
    extracted = sample_extracted_clean()
    result = _result(extracted)
    chk = _check(result, "on_board_date_vs_latest_shipment")
    assert chk is not None
    assert chk.match is True


def test_bl_date_after_latest_shipment_is_major():
    extracted = sample_extracted_clean()
    # Set on_board_date to after latest_shipment_date
    for doc in extracted.documents:
        if doc.document_type == DocumentType.bill_of_lading:
            for f in doc.fields:
                if f.field_name == "on_board_date":
                    f.value = "2026-07-20"   # after 2026-07-10
    result = _result(extracted)
    chk = _check(result, "on_board_date_vs_latest_shipment")
    assert chk is not None
    assert chk.match is False
    assert result.overall_status == "MAJOR_DISCREPANCY"


# ─── Output schema ────────────────────────────────────────────────────────────

def test_result_schema_keys():
    result = _result(sample_extracted_clean())
    assert result.bundle_id == "bundle_clean_01"
    assert result.overall_status in ("CLEAN", "MINOR_DISCREPANCY", "MAJOR_DISCREPANCY")
    assert len(result.comparisons) > 0


def test_all_comparisons_have_required_fields():
    result = _result(sample_extracted_clean())
    for chk in result.comparisons:
        assert chk.field_name
        assert isinstance(chk.match, bool)
        assert 0.0 <= chk.match_score <= 1.0
