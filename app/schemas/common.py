from enum import Enum
from pydantic import BaseModel, ConfigDict


class DocumentType(str, Enum):
    letter_of_credit = "letter_of_credit"
    bill_of_lading = "bill_of_lading"
    commercial_invoice = "commercial_invoice"
    packing_list = "packing_list"
    certificate_of_origin = "certificate_of_origin"
    marine_insurance_certificate = "marine_insurance_certificate"
    inspection_certificate = "inspection_certificate"
    sanctions_policy = "sanctions_policy"


class Severity(str, Enum):
    major = "major"
    minor = "minor"
    warning = "warning"
    info = "info"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class BaseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True, json_encoders={})

    def model_dump_sorted(self) -> dict:
        import json
        return json.loads(self.model_dump_json())


class BoundingBox(BaseSchema):
    x0: float
    y0: float
    x1: float
    y1: float
    page: int
