from app.schemas.common import BoundingBox
from app.schemas.context import EvidenceItem


def make_evidence_item(
    file: str,
    page: int,
    field: str,
    value: str,
    bbox: BoundingBox = None,
) -> EvidenceItem:
    return EvidenceItem(
        file=file,
        page=page,
        field=field,
        value=value,
        bbox=bbox.model_dump() if bbox else None,
    )
