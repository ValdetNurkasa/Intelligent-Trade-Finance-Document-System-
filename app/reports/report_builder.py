from app.state import PipelineState
from app.utils.io import write_text


def build_run_report(state: PipelineState) -> str:
    decision = state.final_decision.decision if state.final_decision else "PENDING"
    fd = state.final_decision

    lines = [
        "# ITFDS Run Report",
        "",
        f"**Bundle ID:** {state.bundle_id}",
        f"**Decision:** {decision}",
        "",
        "## Findings Summary",
        "",
    ]

    if fd:
        lines += [
            "| Category | Count |",
            "|----------|-------|",
            f"| Major findings | {fd.findings_summary.major} |",
            f"| Minor findings | {fd.findings_summary.minor} |",
            f"| Warnings | {fd.findings_summary.warnings} |",
            f"| Sanctions hits | {fd.findings_summary.sanctions_hits} |",
            "",
            f"**Basis:** {fd.decision_basis}",
            "",
        ]

    if state.context:
        ctx = state.context
        lines += [
            "## Transaction Details",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| L/C Number | {ctx.lc_number} |",
            f"| Amount | {ctx.currency} {ctx.amount:,.2f} |",
            f"| Expiry Date | {ctx.expiry_date} |",
            f"| Applicant | {ctx.applicant.name} |",
            f"| Beneficiary | {ctx.beneficiary.name} |",
            f"| Vessel | {ctx.vessel.name} |",
            f"| Risk Level | {ctx.risk_level.value} |",
            "",
        ]

    if state.ucp_result:
        ucp = state.ucp_result
        lines += [
            "## UCP 600 Compliance",
            "",
            f"**Overall Compliant:** {'Yes' if ucp.overall_compliant else 'No'}",
            f"Rules checked: {ucp.rules_checked} | Passed: {ucp.rules_passed} | Failed: {ucp.rules_failed}",
            "",
        ]
        for r in ucp.results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"- [{status}] {r.rule_id} — {r.rule_name}")
        lines.append("")

    if state.sanctions:
        sc = state.sanctions
        lines += [
            "## Sanctions Screening",
            "",
            f"**Status:** {sc.overall_status}",
            f"**Entities screened:** {sc.entities_screened}",
            f"**Hits:** {len(sc.hits)}",
            "",
        ]

    if state.warnings:
        lines += [
            "## Warnings",
            "",
        ]
        for w in state.warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def write_run_report(state: PipelineState) -> None:
    report = build_run_report(state)
    reports_dir = state.run_dir / "reports"
    reports_dir.mkdir(exist_ok=True)
    write_text(reports_dir / "run_report.md", report)
