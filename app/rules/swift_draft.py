from app.schemas.context import ContextPacket
from app.schemas.decision import FinalDecision
from app.schemas.findings import Finding


def generate_swift(context: ContextPacket, decision: FinalDecision) -> str:
    mt = decision.swift_message_type or "MT799"
    lines = []
    lines.append("{1:F01XXXXXXXXAXXX0000000000}")
    lines.append(f"{{2:I{mt[2:]}XXXXXXXXXXXXN}}")
    lines.append("{4:")
    lines.append(f":20:{context.lc_number}")
    lines.append(f":21:{context.lc_number}")
    if mt == "MT700":
        lines.append(":31C:" + (context.expiry_date or ""))
        lines.append(f":32B:{context.currency}{context.amount:.2f}")
        lines.append(f":50:{context.applicant.name}")
        lines.append(f":59:{context.beneficiary.name}")
        lines.append(":71B:HONOUR - DOCUMENTS COMPLY")
    elif mt == "MT752":
        lines.append(f":32B:{context.currency}{context.amount:.2f}")
        lines.append(f":50:{context.applicant.name}")
        lines.append(f":59:{context.beneficiary.name}")
        lines.append(":77J:DISCREPANCIES NOTED - SEE :77A:")
        lines.append(":77A:" + decision.decision_basis)
    else:
        lines.append(":79:" + decision.decision_basis)
    lines.append("-}")
    return "\n".join(lines)


def generate_discrepancies_md(
    context: ContextPacket,
    decision: FinalDecision,
    findings: list[Finding],
) -> str:
    lines = []
    lines.append(f"# Discrepancy Report — {context.lc_number}")
    lines.append("")
    lines.append(f"**Bundle:** {context.bundle_id}")
    lines.append(f"**Decision:** {decision.decision}")
    lines.append(f"**Basis:** {decision.decision_basis}")
    lines.append("")
    lines.append(f"**Summary:** {decision.findings_summary.major} major, "
                 f"{decision.findings_summary.minor} minor, "
                 f"{decision.findings_summary.warnings} warning(s), "
                 f"{decision.findings_summary.sanctions_hits} sanctions hit(s)")
    lines.append("")
    if not findings:
        lines.append("No discrepancies identified. All documents comply with the credit terms.")
        return "\n".join(lines)
    lines.append("## Findings")
    lines.append("")
    for f in sorted(findings, key=lambda x: (x.severity.value, x.rule)):
        lines.append(f"### [{f.severity.value.upper()}] {f.rule}")
        lines.append(f"- **Finding ID:** {f.finding_id}")
        lines.append(f"- **Description:** {f.description}")
        lines.append(f"- **Recommendation:** {f.recommendation}")
        lines.append(f"- **Evidence:** {f.evidence.file} (page {f.evidence.page}, field `{f.evidence.field}`)")
        if f.evidence.value_found:
            lines.append(f"  - Found: `{f.evidence.value_found}`")
        if f.evidence.value_expected:
            lines.append(f"  - Expected: `{f.evidence.value_expected}`")
        lines.append("")
    return "\n".join(lines)
