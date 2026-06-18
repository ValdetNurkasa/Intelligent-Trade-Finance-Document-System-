"""Tests for P2 tools: calculator_tool and fuzzy_match_tool."""
import pytest
from app.tools.calculator_tool import parse_amount, within_tolerance, amount_difference_pct
from app.tools.fuzzy_match_tool import similarity, is_match, normalize, compare


# ─── calculator_tool ─────────────────────────────────────────────────────────

def test_parse_amount_plain():
    assert parse_amount("250000.00") == pytest.approx(250000.00)


def test_parse_amount_with_commas():
    assert parse_amount("250,000.00") == pytest.approx(250000.00)


def test_parse_amount_with_currency_prefix():
    assert parse_amount("USD 250,000.00") == pytest.approx(250000.00)


def test_parse_amount_symbol():
    assert parse_amount("$50,000") == pytest.approx(50000.00)


def test_parse_amount_none():
    assert parse_amount(None) is None


def test_parse_amount_empty():
    assert parse_amount("") is None


def test_within_tolerance_exact():
    assert within_tolerance(250000.00, 250000.00, 0.5) is True


def test_within_tolerance_within():
    assert within_tolerance(251250.00, 250000.00, 0.5) is True   # exactly 0.5 %


def test_within_tolerance_exceeds():
    assert within_tolerance(252500.00, 250000.00, 0.5) is False   # 1.0 %


def test_within_tolerance_tight():
    assert within_tolerance(251250.00, 250000.00, 0.3) is False   # 0.5 % > 0.3 %


def test_amount_difference_pct_positive():
    result = amount_difference_pct(251250.00, 250000.00)
    assert result == pytest.approx(0.5, abs=0.01)


def test_amount_difference_pct_negative():
    result = amount_difference_pct(248750.00, 250000.00)
    assert result == pytest.approx(-0.5, abs=0.01)


# ─── fuzzy_match_tool ────────────────────────────────────────────────────────

def test_normalize_lowercases():
    assert normalize("ABC Trading Co.") == "abc trading co"


def test_normalize_collapses_spaces():
    assert normalize("  hello   world  ") == "hello world"


def test_similarity_identical():
    assert similarity("ABC Exports Ltd", "ABC Exports Ltd") == pytest.approx(1.0)


def test_similarity_case_insensitive():
    # similarity() wraps token_sort_ratio without normalizing; use normalize() first
    from app.tools.fuzzy_match_tool import normalize
    score = similarity(normalize("abc exports ltd"), normalize("ABC Exports Ltd"))
    assert score == pytest.approx(1.0)


def test_similarity_variation():
    score = similarity("Shenzhen Lition Electronics Co Ltd", "Shenzhen Lition Electronics Company Ltd")
    assert score > 0.8


def test_similarity_mismatch():
    score = similarity("ABC Corp", "XYZ Imports Inc")
    assert score < 0.5


def test_is_match_exact():
    assert is_match("ABC Exports Ltd", "ABC Exports Ltd") is True


def test_is_match_variation():
    assert is_match("Shenzhen Lition Electronics Co Ltd",
                    "Shenzhen Lition Electronics Company Ltd") is True


def test_is_match_mismatch():
    assert is_match("ABC Corp", "XYZ Imports Inc") is False


def test_compare_match():
    result = compare("ABC Exports Ltd", "ABC Exports Ltd")
    assert result["match"] is True
    assert result["score"] == pytest.approx(1.0)
    assert result["notes"] is None


def test_compare_missing_value():
    result = compare("", "ABC Exports Ltd")
    assert result["match"] is False
    assert "missing" in result["notes"]


def test_compare_threshold_respected():
    result = compare("ABC Exports Ltd", "ABC Exports Ltd", threshold=0.99)
    assert result["match"] is True
