from typing import Optional
from app.schemas.common import BaseSchema, BoundingBox, DocumentType


class ExtractedField(BaseSchema):
    field_name: str
    value: str
    confidence: float
    page: int
    bounding_box: Optional[BoundingBox] = None
    low_confidence: bool = False
    manual_review_required: bool = False
    llm_derived: bool = False


class ExtractedDocument(BaseSchema):
    document_type: DocumentType
    file: str
    fields: list[ExtractedField]


class ExtractedDocs(BaseSchema):
    bundle_id: str
    documents: list[ExtractedDocument]
