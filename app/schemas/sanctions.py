from typing import Optional
from app.schemas.common import BaseSchema, RiskLevel


class SanctionsHit(BaseSchema):
    entity_name: str
    entity_type: str
    list_name: str
    match_score: float
    match_type: str
    is_false_positive: bool
    false_positive_reason: Optional[str] = None
    recommended_action: str


class SanctionsScreen(BaseSchema):
    bundle_id: str
    overall_status: str
    freeze_processing: bool
    risk_level: RiskLevel
    entities_screened: int
    hits: list[SanctionsHit]
    countries_flagged: list[str]
    dual_use_flags: list[str]
