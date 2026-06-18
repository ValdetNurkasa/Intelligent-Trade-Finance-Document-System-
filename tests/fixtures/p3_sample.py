from app.schemas.common import DocumentType, RiskLevel
from app.schemas.context import (
    ContextPacket,
    Party,
    Vessel,
    Ports,
    LCFlags,
    DocumentRef,
    EvidenceItem,
)
from app.schemas.extraction import (
    ExtractedDocs,
    ExtractedDocument,
    ExtractedField,
)


def sample_context(bundle_id: str = "bundle_002_bl_expiry") -> ContextPacket:
    return ContextPacket(
        bundle_id=bundle_id,
        lc_number="LC-2026-00042",
        currency="USD",
        amount=250000.00,
        expiry_date="2026-05-31",
        latest_shipment_date="2026-05-20",
        presentation_period_days=21,
        incoterms="CIF",
        ucp_version="UCP600",
        applicant=Party(
            name="Adriatic Imports Sh.p.k.",
            address="Rr. Nene Tereza 12, Prishtina, Kosovo",
            country="XK",
        ),
        beneficiary=Party(
            name="Shenzhen Lition Electronics Co Ltd",
            address="Bao'an District, Shenzhen, China",
            country="CN",
        ),
        issuing_bank=Party(
            name="Banka Kombetare Tregtare",
            address="Prishtina, Kosovo",
            swift="NCBAXKPRXXX",
            country="XK",
        ),
        advising_bank=Party(
            name="Bank of China",
            address="Shenzhen, China",
            swift="BKCHCNBJ45A",
            country="CN",
        ),
        vessel=Vessel(
            name="MV Adriatic Star",
            imo="9123456",
            flag_state="Panama",
            voyage="V-208E",
        ),
        ports=Ports(loading="Shenzhen, CN", discharge="Durres, AL"),
        flags=LCFlags(
            partial_shipment_allowed=False,
            transhipment_allowed=False,
            tolerance_percent=5.0,
        ),
        documents=[
            DocumentRef(type=DocumentType.letter_of_credit, file="lc.pdf"),
            DocumentRef(type=DocumentType.commercial_invoice, file="invoice.pdf"),
            DocumentRef(type=DocumentType.bill_of_lading, file="bill_of_lading.pdf"),
            DocumentRef(type=DocumentType.packing_list, file="packing_list.pdf"),
            DocumentRef(type=DocumentType.certificate_of_origin, file="cert_origin.pdf"),
        ],
        evidence_index={
            "lc.expiry_date": EvidenceItem(
                file="lc.pdf", page=1, field="expiry_date", value="2026-05-31"
            ),
            "bill_of_lading.shipment_date": EvidenceItem(
                file="bill_of_lading.pdf", page=1, field="shipment_date", value="2026-06-08"
            ),
        },
        risk_flags=[],
        risk_level=RiskLevel.low,
    )


def sample_extracted(bundle_id: str = "bundle_002_bl_expiry") -> ExtractedDocs:
    return ExtractedDocs(
        bundle_id=bundle_id,
        documents=[
            ExtractedDocument(
                document_type=DocumentType.letter_of_credit,
                file="lc.pdf",
                fields=[
                    ExtractedField(field_name="lc_number", value="LC-2026-00042", confidence=0.99, page=1),
                    ExtractedField(field_name="expiry_date", value="2026-05-31", confidence=0.98, page=1),
                    ExtractedField(field_name="latest_shipment_date", value="2026-05-20", confidence=0.97, page=1),
                    ExtractedField(field_name="amount", value="250000.00", confidence=0.98, page=1),
                    ExtractedField(field_name="currency", value="USD", confidence=0.99, page=1),
                ],
            ),
            ExtractedDocument(
                document_type=DocumentType.commercial_invoice,
                file="invoice.pdf",
                fields=[
                    ExtractedField(field_name="invoice_amount", value="250000.00", confidence=0.96, page=1),
                    ExtractedField(field_name="currency", value="USD", confidence=0.99, page=1),
                    ExtractedField(field_name="beneficiary", value="Shenzhen Lition Electronics Co Ltd", confidence=0.95, page=1),
                ],
            ),
            ExtractedDocument(
                document_type=DocumentType.bill_of_lading,
                file="bill_of_lading.pdf",
                fields=[
                    ExtractedField(field_name="shipment_date", value="2026-06-08", confidence=0.94, page=1),
                    ExtractedField(field_name="presentation_date", value="2026-06-10", confidence=0.93, page=1),
                    ExtractedField(field_name="port_of_loading", value="Shenzhen, CN", confidence=0.95, page=1),
                    ExtractedField(field_name="port_of_discharge", value="Durres, AL", confidence=0.95, page=1),
                    ExtractedField(field_name="partial_shipment", value="false", confidence=0.9, page=1),
                    ExtractedField(field_name="transhipment", value="false", confidence=0.9, page=1),
                ],
            ),
        ],
    )


def sample_context_sanctioned(bundle_id: str = "bundle_006_sanctions_hit") -> ContextPacket:
    ctx = sample_context(bundle_id)
    ctx.vessel = Vessel(
        name="MV Crimson Star",
        imo="9555888",
        flag_state="Iran",
        voyage="V-77W",
    )
    ctx.beneficiary = Party(
        name="Crimson Star Shipping Ltd",
        address="Bandar Abbas, Iran",
        country="IR",
    )
    return ctx
