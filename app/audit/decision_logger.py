from pathlib import Path
from app.schemas.context import ContextPacket
from app.schemas.decision import FinalDecision
from app.schemas.findings import Finding
from app.utils.io import write_text


def build_rationale(
    context: ContextPacket,
    decision: FinalDecision,
    findings: list[Finding],
) -> str:
    s = decision.findings_summary
    steps = []
    steps.append(f"Sanctions hits (actionable): {s.sanctions_hits}")
    steps.append(f"Major discrepancies: {s.major}")
    steps.append(f"Minor discrepancies: {s.minor}")
    steps.append(f"Warnings: {s.warnings}")

    if decision.decision == "FREEZE":
        reason = "An actionable sanctions hit was detected. Sanctions screening takes precedence over all other checks, so processing is frozen pending compliance review."
    elif decision.decision == "REFUSE" and s.major > 0:
        reason = "One or more major discrepancies were found. Major discrepancies mean the documents do not comply with the credit terms, so the presentation is refused."
    elif decision.decision == "REFUSE":
        reason = "The number of minor discrepancies exceeded the approval threshold defined in the policy pack, so the presentation is refused."
    elif decision.decision == "HONOUR" and (s.minor > 0 or s.warnings > 0):
        reason = "Only minor discrepancies or warnings were found, within the approval threshold. The presentation is honoured with noted exceptions."
    else:
        reason = "No discrepancies and no sanctions hits were found. The documents comply with the credit terms, so the presentation is honoured."

    return reason


def generate_decision_log(
    context: ContextPacket,
    decision: FinalDecision,
    findings: list[Finding],
) -> str:
    rationale = build_rationale(context, decision, findings)
    s = decision.findings_summary
    lines = []
    lines.append(f"# Decision Log — {context.lc_number}")
    lines.append("")
    lines.append(f"**Bundle:** {context.bundle_id}")
    lines.append(f"**Final decision:** {decision.decision}")
    lines.append(f"**SWIFT message type:** {decision.swift_message_type or 'NONE'}")
    lines.append("")
    lines.append("## Decision basis")
    lines.append(decision.decision_basis)
    lines.append("")
    lines.append("## Rationale")
    lines.append(rationale)
    lines.append("")
    lines.append("## Evaluation order")
    lines.append("1. Sanctions screening (freeze overrides all)")
    lines.append("2. Major discrepancies (force refusal)")
    lines.append("3. Minor discrepancies vs approval threshold")
    lines.append("4. Otherwise honour")
    lines.append("")
    lines.append("## Findings summary")
    lines.append(f"- Sanctions hits (actionable): {s.sanctions_hits}")
    lines.append(f"- Major: {s.major}")
    lines.append(f"- Minor: {s.minor}")
    lines.append(f"- Warnings: {s.warnings}")
    lines.append("")
    if findings:
        lines.append("## Contributing findings")
        for f in sorted(findings, key=lambda x: (x.severity.value, x.rule)):
            lines.append(f"- [{f.severity.value.upper()}] {f.rule} ({f.finding_id}): {f.description}")
    else:
        lines.append("## Contributing findings")
        lines.append("- None")
    return "\n".join(lines)


def log_decision(
    run_dir: Path,
    context: ContextPacket,
    decision: FinalDecision,
    findings: list[Finding],
) -> str:
    content = generate_decision_log(context, decision, findings)
    write_text(run_dir / "decision_log.md", content)
    return build_rationale(context, decision, findings)
