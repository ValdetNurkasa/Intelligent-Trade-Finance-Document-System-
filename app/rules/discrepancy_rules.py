from app.schemas.common import Severity
from app.schemas.findings import Finding
from app.schemas.ucp import UCPResult
from app.schemas.matching import MatchResult
from app.schemas.sanctions import SanctionsScreen


WAIVABLE_RULES = {
    "UCP600-31-partial",
    "UCP600-20-transhipment",
}


def collect_findings(
    ucp_result: UCPResult | None,
    match_result: MatchResult | None,
    sanctions: SanctionsScreen | None,
) -> list[Finding]:
    findings: list[Finding] = []
    if ucp_result is not None:
        for r in ucp_result.results:
            if not r.passed:
                findings.append(r.finding)
    if match_result is not None:
        for comp in match_result.comparisons:
            if not comp.match:
                findings.append(_finding_from_comparison(comp))
    return findings


def _finding_from_comparison(comp) -> Finding:
    from app.schemas.findings import EvidencePointer
    from app.utils.ids import make_finding_id

    return Finding(
        finding_id=make_finding_id("agent_d", comp.field_name, comp.field_name, str(comp.match_score)),
        rule=f"MATCH-{comp.field_name}",
        severity=comp.severity,
        confidence=1.0,
        description=comp.notes or f"Cross-document mismatch on {comp.field_name}.",
        recommendation="Review inconsistent values across documents.",
        source_agent="agent_d",
        evidence=EvidencePointer(
            document_type="multiple",
            file=comp.documents_compared[0] if comp.documents_compared else "unknown",
            page=1,
            field=comp.field_name,
        ),
    )


def classify(finding: Finding) -> str:
    if finding.severity == Severity.major:
        return "major"
    if finding.severity == Severity.minor:
        return "minor"
    return "warning"


def is_waivable(finding: Finding) -> bool:
    if finding.severity == Severity.major:
        return False
    return finding.rule in WAIVABLE_RULES or finding.severity == Severity.minor


def summarize(findings: list[Finding], sanctions: SanctionsScreen | None) -> dict:
    major = sum(1 for f in findings if classify(f) == "major")
    minor = sum(1 for f in findings if classify(f) == "minor")
    warnings = sum(1 for f in findings if classify(f) == "warning")
    sanctions_hits = 0
    if sanctions is not None:
        sanctions_hits = sum(1 for h in sanctions.hits if not h.is_false_positive)
    return {
        "major": major,
        "minor": minor,
        "warnings": warnings,
        "sanctions_hits": sanctions_hits,
    }
