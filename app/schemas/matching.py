from typing import Optional
from app.schemas.common import BaseSchema, Severity


class DocumentValue(BaseSchema):
    document: str
    value: str


class Comparison(BaseSchema):
    field_name: str
    documents_compared: list[str]
    values: list[DocumentValue]
    match: bool
    match_score: float
    severity: Severity
    notes: Optional[str] = None


class MatchResult(BaseSchema):
    bundle_id: str
    overall_status: str
    comparisons: list[Comparison]
