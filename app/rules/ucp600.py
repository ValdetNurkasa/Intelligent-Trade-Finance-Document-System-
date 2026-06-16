from app.schemas.common import Severity
from app.schemas.context import ContextPacket
from app.schemas.extraction import ExtractedDocs
from app.schemas.findings import Finding, EvidencePointer
from app.schemas.ucp import UCPRuleResult, UCPResult
from app.utils.dates import parse_date
from app.utils.ids import make_finding_id


def _field(extracted: ExtractedDocs, doc_type_value: str, field_name: str):
    for doc in extracted.documents:
        if doc.document_type.value == doc_type_value:
            for f in doc.fields:
                if f.field_name == field_name:
                    return doc.file, f
    return None, None


def _passing_result(rule_id: str, rule_name: str, agent: str) -> UCPRuleResult:
    finding = Finding(
        finding_id=make_finding_id(agent, rule_id, "", "pass"),
        rule=rule_id,
        severity=Severity.info,
        confidence=1.0,
        description=f"{rule_name} satisfied.",
        recommendation="No action required.",
        source_agent=agent,
        evidence=EvidencePointer(
            document_type="letter_of_credit",
            file="lc.pdf",
            page=1,
            field=rule_id,
        ),
    )
    return UCPRuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        passed=True,
        severity=Severity.info,
        finding=finding,
    )


def _failing_result(
    rule_id: str,
    rule_name: str,
    severity: Severity,
    description: str,
    recommendation: str,
    evidence: EvidencePointer,
    agent: str,
) -> UCPRuleResult:
    finding = Finding(
        finding_id=make_finding_id(agent, rule_id, evidence.field, evidence.value_found or ""),
        rule=rule_id,
        severity=severity,
        confidence=1.0,
        description=description,
        recommendation=recommendation,
        source_agent=agent,
        evidence=evidence,
    )
    return UCPRuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        passed=False,
        severity=severity,
        finding=finding,
    )


def check_expiry(context: ContextPacket, extracted: ExtractedDocs, agent: str) -> UCPRuleResult:
    rule_id = "UCP600-6c-expiry"
    rule_name = "Credit expiry date"
    file, bl_ship = _field(extracted, "bill_of_lading", "shipment_date")
    expiry = parse_date(context.expiry_date)
    if bl_ship is None or expiry is None:
        return _passing_result(rule_id, rule_name, agent)
    shipment = parse_date(bl_ship.value)
    if shipment is not None and shipment > expiry:
        return _failing_result(
            rule_id,
            rule_name,
            Severity.major,
            f"Shipment date {bl_ship.value} is after L/C expiry {context.expiry_date}.",
            "Refuse documents or seek applicant waiver for late shipment.",
            EvidencePointer(
                document_type="bill_of_lading",
                file=file,
                page=bl_ship.page,
                field="shipment_date",
                value_found=bl_ship.value,
                value_expected=f"on or before {context.expiry_date}",
            ),
            agent,
        )
    return _passing_result(rule_id, rule_name, agent)


def check_latest_shipment(context: ContextPacket, extracted: ExtractedDocs, agent: str) -> UCPRuleResult:
    rule_id = "UCP600-latest-shipment"
    rule_name = "Latest shipment date"
    if context.latest_shipment_date is None:
        return _passing_result(rule_id, rule_name, agent)
    file, bl_ship = _field(extracted, "bill_of_lading", "shipment_date")
    latest = parse_date(context.latest_shipment_date)
    if bl_ship is None or latest is None:
        return _passing_result(rule_id, rule_name, agent)
    shipment = parse_date(bl_ship.value)
    if shipment is not None and shipment > latest:
        return _failing_result(
            rule_id,
            rule_name,
            Severity.major,
            f"Shipment date {bl_ship.value} is after latest shipment date {context.latest_shipment_date}.",
            "Refuse documents or seek applicant waiver for late shipment.",
            EvidencePointer(
                document_type="bill_of_lading",
                file=file,
                page=bl_ship.page,
                field="shipment_date",
                value_found=bl_ship.value,
                value_expected=f"on or before {context.latest_shipment_date}",
            ),
            agent,
        )
    return _passing_result(rule_id, rule_name, agent)


def check_presentation_period(context: ContextPacket, extracted: ExtractedDocs, agent: str) -> UCPRuleResult:
    rule_id = "UCP600-14c-presentation"
    rule_name = "Presentation period (21-day rule)"
    file, bl_ship = _field(extracted, "bill_of_lading", "shipment_date")
    _, pres = _field(extracted, "bill_of_lading", "presentation_date")
    if bl_ship is None or pres is None:
        return _passing_result(rule_id, rule_name, agent)
    shipment = parse_date(bl_ship.value)
    presentation = parse_date(pres.value)
    expiry = parse_date(context.expiry_date)
    if shipment is None or presentation is None:
        return _passing_result(rule_id, rule_name, agent)
    period = context.presentation_period_days or 21
    days_after = (presentation - shipment).days
    over_period = days_after > period
    over_expiry = expiry is not None and presentation > expiry
    if over_period or over_expiry:
        reason = []
        if over_period:
            reason.append(f"{days_after} days after shipment exceeds the {period}-day period")
        if over_expiry:
            reason.append(f"presented {pres.value} after expiry {context.expiry_date}")
        return _failing_result(
            rule_id,
            rule_name,
            Severity.major,
            "Late presentation: " + "; ".join(reason) + ".",
            "Issue refusal advice for late presentation under UCP 600 Article 14(c).",
            EvidencePointer(
                document_type="bill_of_lading",
                file=file,
                page=pres.page,
                field="presentation_date",
                value_found=pres.value,
                value_expected=f"within {period} days of {bl_ship.value} and on or before {context.expiry_date}",
            ),
            agent,
        )
    return _passing_result(rule_id, rule_name, agent)


def check_partial_shipment(context: ContextPacket, extracted: ExtractedDocs, agent: str) -> UCPRuleResult:
    rule_id = "UCP600-31-partial"
    rule_name = "Partial shipment restriction"
    if context.flags.partial_shipment_allowed:
        return _passing_result(rule_id, rule_name, agent)
    file, partial = _field(extracted, "bill_of_lading", "partial_shipment")
    if partial is None:
        return _passing_result(rule_id, rule_name, agent)
    if str(partial.value).strip().lower() in ("true", "yes", "1"):
        return _failing_result(
            rule_id,
            rule_name,
            Severity.major,
            "Partial shipment presented but the L/C prohibits partial shipment.",
            "Refuse documents; partial shipment is not permitted under the credit.",
            EvidencePointer(
                document_type="bill_of_lading",
                file=file,
                page=partial.page,
                field="partial_shipment",
                value_found=partial.value,
                value_expected="false",
            ),
            agent,
        )
    return _passing_result(rule_id, rule_name, agent)


def check_transhipment(context: ContextPacket, extracted: ExtractedDocs, agent: str) -> UCPRuleResult:
    rule_id = "UCP600-20-transhipment"
    rule_name = "Transhipment restriction"
    if context.flags.transhipment_allowed:
        return _passing_result(rule_id, rule_name, agent)
    file, trans = _field(extracted, "bill_of_lading", "transhipment")
    if trans is None:
        return _passing_result(rule_id, rule_name, agent)
    if str(trans.value).strip().lower() in ("true", "yes", "1"):
        return _failing_result(
            rule_id,
            rule_name,
            Severity.major,
            "Transhipment indicated but the L/C prohibits transhipment.",
            "Refuse documents; transhipment is not permitted under the credit.",
            EvidencePointer(
                document_type="bill_of_lading",
                file=file,
                page=trans.page,
                field="transhipment",
                value_found=trans.value,
                value_expected="false",
            ),
            agent,
        )
    return _passing_result(rule_id, rule_name, agent)


ALL_CHECKS = [
    check_expiry,
    check_latest_shipment,
    check_presentation_period,
    check_partial_shipment,
    check_transhipment,
]


def run_ucp_checks(context: ContextPacket, extracted: ExtractedDocs, agent: str = "agent_c") -> UCPResult:
    results = [check(context, extracted, agent) for check in ALL_CHECKS]
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    return UCPResult(
        bundle_id=context.bundle_id,
        overall_compliant=failed == 0,
        rules_checked=len(results),
        rules_passed=passed,
        rules_failed=failed,
        results=results,
    )
