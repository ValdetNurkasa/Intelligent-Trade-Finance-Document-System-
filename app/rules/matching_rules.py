from __future__ import annotations
from typing import Optional

from app.config import settings
from app.schemas.common import Severity
from app.schemas.extraction import ExtractedDocs
from app.schemas.matching import Comparison, DocumentValue, MatchResult
from app.tools.fuzzy_match_tool import compare as fuzzy_compare, THRESHOLD
from app.tools.calculator_tool import parse_amount, within_tolerance, amount_difference_pct
from app.utils.dates import parse_date


# ─── Field lookup helper ──────────────────────────────────────────────────────

def _get(extracted: ExtractedDocs, doc_type_value: str, field_name: str) -> Optional[str]:
    for doc in extracted.documents:
        if doc.document_type.value == doc_type_value:
            for f in doc.fields:
                if f.field_name == field_name and f.value:
                    return f.value
    return None


def _doc_values(extracted: ExtractedDocs, field_name: str,
                *doc_types: str) -> list[DocumentValue]:
    out = []
    for dt in doc_types:
        val = _get(extracted, dt, field_name)
        if val:
            out.append(DocumentValue(document=dt, value=val))
    return out


# ─── Individual comparison builders ──────────────────────────────────────────

def _string_check(field_name: str, documents_compared: list[str],
                  values: list[DocumentValue], threshold: float = THRESHOLD) -> Comparison:
    if len(values) < 2:
        return Comparison(
            field_name=field_name, documents_compared=documents_compared,
            values=values, match=False, match_score=0.0,
            severity=Severity.warning,
            notes="field missing in one or more documents",
        )
    a, b = values[0].value, values[1].value
    result = fuzzy_compare(a, b, threshold=threshold)
    severity = Severity.info if result["match"] else Severity.minor
    return Comparison(
        field_name=field_name, documents_compared=documents_compared,
        values=values, match=result["match"],
        match_score=result["score"], severity=severity,
        notes=result["notes"],
    )


def _amount_check(field_name: str, documents_compared: list[str],
                  values: list[DocumentValue],
                  tolerance_pct: float) -> Comparison:
    if len(values) < 2:
        return Comparison(
            field_name=field_name, documents_compared=documents_compared,
            values=values, match=False, match_score=0.0,
            severity=Severity.warning,
            notes="amount field missing in one or more documents",
        )
    a = parse_amount(values[0].value)
    b = parse_amount(values[1].value)
    if a is None or b is None:
        return Comparison(
            field_name=field_name, documents_compared=documents_compared,
            values=values, match=False, match_score=0.0,
            severity=Severity.major, notes="could not parse amount as number",
        )
    ok = within_tolerance(a, b, tolerance_pct)
    diff = amount_difference_pct(a, b)
    score = 1.0 - min(1.0, abs(diff) / 10.0)
    notes = None if ok else f"difference {diff:+.2f}% exceeds tolerance {tolerance_pct}%"
    return Comparison(
        field_name=field_name, documents_compared=documents_compared,
        values=values, match=ok, match_score=round(score, 4),
        severity=Severity.info if ok else Severity.major,
        notes=notes,
    )


def _date_lte_check(field_name: str, documents_compared: list[str],
                    values: list[DocumentValue]) -> Comparison:
    """Check date_a <= date_b (e.g. on_board_date <= latest_shipment_date)."""
    if len(values) < 2:
        return Comparison(
            field_name=field_name, documents_compared=documents_compared,
            values=values, match=False, match_score=0.0,
            severity=Severity.warning,
            notes="date field missing in one or more documents",
        )
    d_a = parse_date(values[0].value)
    d_b = parse_date(values[1].value)
    if d_a is None or d_b is None:
        return Comparison(
            field_name=field_name, documents_compared=documents_compared,
            values=values, match=False, match_score=0.0,
            severity=Severity.major, notes="could not parse date(s)",
        )
    ok = d_a <= d_b
    days = (d_b - d_a).days
    notes = None if ok else f"date is {-days} day(s) after deadline"
    return Comparison(
        field_name=field_name, documents_compared=documents_compared,
        values=values, match=ok, match_score=1.0 if ok else 0.0,
        severity=Severity.info if ok else Severity.major,
        notes=notes,
    )


# ─── Full rule set ────────────────────────────────────────────────────────────

def run_matching(extracted: ExtractedDocs, tolerance_pct: float = 5.0) -> MatchResult:
    """
    Execute all cross-document consistency checks and return a MatchResult.
    """
    inv  = "commercial_invoice"
    bol  = "bill_of_lading"
    pl   = "packing_list"
    coo  = "certificate_of_origin"
    lc   = "letter_of_credit"
    comparisons: list[Comparison] = []

    # CHK-01  goods description: invoice vs B/L
    chk01_vals = _doc_values(extracted, "goods_description", inv, bol)
    chk01 = _string_check("goods_description", [inv, bol], chk01_vals)
    if settings.USE_LLM and chk01.match and len(chk01_vals) == 2:
        from app.llm.semantic_judge import judge_descriptions
        verdict = judge_descriptions(chk01_vals[0].value, chk01_vals[1].value)
        if verdict["flag_for_review"]:
            chk01 = Comparison(
                field_name=chk01.field_name,
                documents_compared=chk01.documents_compared,
                values=chk01.values,
                match=chk01.match,
                match_score=chk01.match_score,
                severity=Severity.warning,
                notes=f"[llm] semantic ambiguity flagged: {verdict['reason']}",
            )
    comparisons.append(chk01)

    # CHK-02  goods description: invoice vs packing list
    comparisons.append(_string_check(
        "goods_description", [inv, pl],
        _doc_values(extracted, "goods_description", inv, pl),
    ))

    # CHK-03  goods description: invoice vs cert of origin
    comparisons.append(_string_check(
        "goods_description", [inv, coo],
        _doc_values(extracted, "goods_description", inv, coo),
    ))

    # CHK-04  quantity: invoice vs packing list
    inv_qty = _get(extracted, inv, "quantity")
    pl_qty  = _get(extracted, pl,  "total_quantity")
    qty_vals = []
    if inv_qty:
        qty_vals.append(DocumentValue(document=inv, value=inv_qty))
    if pl_qty:
        qty_vals.append(DocumentValue(document=pl, value=pl_qty))
    comparisons.append(_string_check("quantity", [inv, pl], qty_vals))

    # CHK-05  amount: invoice vs L/C (with tolerance)
    inv_amount = _get(extracted, inv, "amount")
    lc_amount  = _get(extracted, lc,  "amount")
    amount_vals = []
    if inv_amount:
        amount_vals.append(DocumentValue(document=inv, value=inv_amount))
    if lc_amount:
        amount_vals.append(DocumentValue(document=lc, value=lc_amount))
    comparisons.append(_amount_check("amount", [inv, lc], amount_vals, tolerance_pct))

    # CHK-06  on_board_date <= latest_shipment_date
    obd  = _get(extracted, bol, "on_board_date")
    lsd  = _get(extracted, lc,  "latest_shipment_date")
    date_vals = []
    if obd:
        date_vals.append(DocumentValue(document=bol, value=obd))
    if lsd:
        date_vals.append(DocumentValue(document=lc, value=lsd))
    comparisons.append(_date_lte_check("on_board_date_vs_latest_shipment", [bol, lc], date_vals))

    # CHK-07  invoice_date <= expiry_date
    inv_date = _get(extracted, inv, "invoice_date")
    exp_date = _get(extracted, lc,  "expiry_date")
    inv_date_vals = []
    if inv_date:
        inv_date_vals.append(DocumentValue(document=inv, value=inv_date))
    if exp_date:
        inv_date_vals.append(DocumentValue(document=lc, value=exp_date))
    comparisons.append(_date_lte_check("invoice_date_vs_expiry", [inv, lc], inv_date_vals))

    # CHK-08  beneficiary name: invoice vs L/C
    inv_ben = _get(extracted, inv, "beneficiary_name")
    lc_ben  = _get(extracted, lc,  "beneficiary")
    ben_vals = []
    if inv_ben:
        ben_vals.append(DocumentValue(document=inv, value=inv_ben))
    if lc_ben:
        ben_vals.append(DocumentValue(document=lc, value=lc_ben))
    comparisons.append(_string_check("beneficiary_name", [inv, lc], ben_vals))

    # CHK-09  applicant name: invoice vs L/C
    inv_app = _get(extracted, inv, "applicant_name")
    lc_app  = _get(extracted, lc,  "applicant")
    app_vals = []
    if inv_app:
        app_vals.append(DocumentValue(document=inv, value=inv_app))
    if lc_app:
        app_vals.append(DocumentValue(document=lc, value=lc_app))
    comparisons.append(_string_check("applicant_name", [inv, lc], app_vals))

    # CHK-10  port of loading: invoice vs B/L
    comparisons.append(_string_check(
        "port_of_loading", [inv, bol],
        _doc_values(extracted, "port_of_loading", inv, bol),
    ))

    # CHK-11  port of discharge: invoice vs B/L
    comparisons.append(_string_check(
        "port_of_discharge", [inv, bol],
        _doc_values(extracted, "port_of_discharge", inv, bol),
    ))

    # CHK-12  gross weight: packing list vs B/L
    comparisons.append(_string_check(
        "gross_weight", [pl, bol],
        _doc_values(extracted, "gross_weight", pl, bol),
    ))

    # CHK-13  currency: invoice vs L/C
    comparisons.append(_string_check(
        "currency", [inv, lc],
        _doc_values(extracted, "currency", inv, lc),
    ))

    # Derive overall status
    majors = [c for c in comparisons if c.severity == Severity.major and not c.match]
    minors = [c for c in comparisons if c.severity == Severity.minor and not c.match]

    if majors:
        overall = "MAJOR_DISCREPANCY"
    elif minors:
        overall = "MINOR_DISCREPANCY"
    else:
        overall = "CLEAN"

    return MatchResult(
        bundle_id=extracted.bundle_id,
        overall_status=overall,
        comparisons=comparisons,
    )
