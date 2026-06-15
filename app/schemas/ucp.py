from app.schemas.common import BaseSchema, Severity
from app.schemas.findings import Finding


class UCPRuleResult(BaseSchema):
    rule_id: str
    rule_name: str
    passed: bool
    severity: Severity
    finding: Finding


class UCPResult(BaseSchema):
    bundle_id: str
    overall_compliant: bool
    rules_checked: int
    rules_passed: int
    rules_failed: int
    results: list[UCPRuleResult]
