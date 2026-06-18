from __future__ import annotations
import re
from typing import Optional

_STRIP = re.compile(r"[^\d.]")


def parse_amount(value: str) -> Optional[float]:
    """Parse a currency string like 'USD 50,000.00' or '$50,000' to float."""
    if not value:
        return None
    cleaned = _STRIP.sub("", value.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


def within_tolerance(amount: float, reference: float, tolerance_pct: float) -> bool:
    """True if amount is within ±tolerance_pct % of reference."""
    if reference == 0:
        return amount == 0
    return abs(amount - reference) / abs(reference) * 100 <= tolerance_pct


def amount_difference_pct(amount: float, reference: float) -> float:
    """Signed % difference: (amount - reference) / reference * 100."""
    if reference == 0:
        return 0.0
    return round((amount - reference) / abs(reference) * 100, 4)
