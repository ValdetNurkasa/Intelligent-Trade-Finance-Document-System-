from typing import Optional
from app.schemas.common import BaseSchema, Severity


class EvidencePointer(BaseSchema):
    document_type: str
    file: str
    page: int
    field: str
    value_found: Optional[str] = None
    value_expected: Optional[str] = None


class Finding(BaseSchema):
    finding_id: str
    rule: str
    severity: Severity
    confidence: float
    description: str
    recommendation: str
    source_agent: str
    evidence: EvidencePointer


class AgentFindings(BaseSchema):
    bundle_id: str
    agent: str
    findings: list[Finding]
