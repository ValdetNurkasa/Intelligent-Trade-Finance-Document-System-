from typing import Optional
from app.schemas.common import BaseSchema


class FindingsSummary(BaseSchema):
    major: int
    minor: int
    warnings: int
    sanctions_hits: int


class PostingPayload(BaseSchema):
    bundle_id: str
    lc_number: str
    decision: str
    swift_message_type: str
    discrepancy_count: int
    requires_human_review: bool


class FinalDecision(BaseSchema):
    bundle_id: str
    decision: str
    decision_basis: str
    findings_summary: FindingsSummary
    finding_ids: list[str]
    swift_message_type: Optional[str] = None
    audit_trail: Optional[str] = None
    timestamp: str


class Metrics(BaseSchema):
    bundle_id: str
    run_id: str
    total_documents: int
    total_fields_extracted: int
    low_confidence_fields: int
    extraction_accuracy: float
    discrepancy_rate: float
    processing_time_seconds: float
    decision: str
