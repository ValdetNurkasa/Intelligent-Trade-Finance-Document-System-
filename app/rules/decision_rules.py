from app.schemas.context import ContextPacket
from app.schemas.ucp import UCPResult
from app.schemas.matching import MatchResult
from app.schemas.sanctions import SanctionsScreen
from app.schemas.decision import FinalDecision, FindingsSummary, PostingPayload
from app.rules.discrepancy_rules import collect_findings, summarize


def decide(
    context: ContextPacket,
    ucp_result: UCPResult | None,
    match_result: MatchResult | None,
    sanctions: SanctionsScreen | None,
    policy: dict,
    timestamp: str = "",
) -> FinalDecision:
    findings = collect_findings(ucp_result, match_result, sanctions)
    summary = summarize(findings, sanctions)
    minor_threshold = int(policy.get("approval_threshold_minor", 3))

    freeze = sanctions is not None and sanctions.freeze_processing

    if freeze:
        decision = "FREEZE"
        basis = "Active sanctions hit detected; processing frozen pending compliance review."
        swift_type = None
    elif summary["major"] > 0:
        decision = "REFUSE"
        basis = f"{summary['major']} major discrepancy(ies) identified; documents do not comply with the credit terms."
        swift_type = "MT752"
    elif summary["minor"] > minor_threshold:
        decision = "REFUSE"
        basis = f"{summary['minor']} minor discrepancies exceed the approval threshold of {minor_threshold}."
        swift_type = "MT752"
    elif summary["minor"] > 0 or summary["warnings"] > 0:
        decision = "HONOUR"
        basis = "Minor discrepancies within approval threshold; honour with noted exceptions."
        swift_type = "MT700"
    else:
        decision = "HONOUR"
        basis = "All documents comply with the credit terms; honour payment."
        swift_type = "MT700"

    finding_ids = [f.finding_id for f in findings]

    return FinalDecision(
        bundle_id=context.bundle_id,
        decision=decision,
        decision_basis=basis,
        findings_summary=FindingsSummary(**summary),
        finding_ids=finding_ids,
        swift_message_type=swift_type,
        audit_trail=None,
        timestamp=timestamp,
    )


def build_posting_payload(context: ContextPacket, decision: FinalDecision) -> PostingPayload:
    total_disc = (
        decision.findings_summary.major
        + decision.findings_summary.minor
        + decision.findings_summary.warnings
    )
    requires_review = decision.decision in ("REFUSE", "FREEZE") or total_disc > 0
    return PostingPayload(
        bundle_id=context.bundle_id,
        lc_number=context.lc_number,
        decision=decision.decision,
        swift_message_type=decision.swift_message_type or "NONE",
        discrepancy_count=total_disc,
        requires_human_review=requires_review,
    )
