from typing import Optional
from app.schemas.common import BaseSchema, DocumentType, RiskLevel


class Party(BaseSchema):
    name: str
    address: str
    swift: Optional[str] = None
    country: Optional[str] = None


class Vessel(BaseSchema):
    name: str
    imo: str
    flag_state: str
    voyage: Optional[str] = None


class Ports(BaseSchema):
    loading: str
    discharge: str


class LCFlags(BaseSchema):
    partial_shipment_allowed: bool
    transhipment_allowed: bool
    tolerance_percent: float


class DocumentRef(BaseSchema):
    type: DocumentType
    file: str
    reference: Optional[str] = None
    date: Optional[str] = None


class EvidenceItem(BaseSchema):
    file: str
    page: int
    field: str
    value: str
    bbox: Optional[dict] = None


class ContextPacket(BaseSchema):
    bundle_id: str
    lc_number: str
    currency: str
    amount: float
    expiry_date: str
    latest_shipment_date: Optional[str] = None
    presentation_period_days: int
    incoterms: Optional[str] = None
    ucp_version: Optional[str] = None
    applicant: Party
    beneficiary: Party
    issuing_bank: Party
    advising_bank: Party
    vessel: Vessel
    ports: Ports
    flags: LCFlags
    documents: list[DocumentRef]
    evidence_index: dict[str, EvidenceItem]
    risk_flags: list[str] = []
    risk_level: RiskLevel = RiskLevel.low
