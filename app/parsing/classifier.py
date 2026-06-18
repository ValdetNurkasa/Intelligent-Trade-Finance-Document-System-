from pathlib import Path
from app.schemas.common import DocumentType


FILENAME_MAP = {
    "letter_of_credit": DocumentType.letter_of_credit,
    "bill_of_lading": DocumentType.bill_of_lading,
    "commercial_invoice": DocumentType.commercial_invoice,
    "packing_list": DocumentType.packing_list,
    "certificate_of_origin": DocumentType.certificate_of_origin,
    "marine_insurance": DocumentType.marine_insurance_certificate,
    "inspection": DocumentType.inspection_certificate,
    "sanctions": DocumentType.sanctions_policy,
}


def classify(file_path: Path) -> DocumentType:
    name = file_path.stem.lower()
    for keyword, doc_type in FILENAME_MAP.items():
        if keyword in name:
            return doc_type
    return DocumentType.commercial_invoice
