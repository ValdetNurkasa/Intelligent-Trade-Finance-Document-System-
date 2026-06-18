"""P2 test fixtures – reusable sample objects for extraction + matching tests."""
from app.schemas.common import DocumentType
from app.schemas.extraction import ExtractedDocs, ExtractedDocument, ExtractedField


def sample_extracted_clean(bundle_id: str = "bundle_clean_01") -> ExtractedDocs:
    """All docs present, consistent, high-confidence values."""
    return ExtractedDocs(
        bundle_id=bundle_id,
        documents=[
            ExtractedDocument(
                document_type=DocumentType.commercial_invoice,
                file="invoice.pdf",
                fields=[
                    ExtractedField(field_name="invoice_number",    value="INV-2026-0099",                        confidence=0.92, page=1),
                    ExtractedField(field_name="amount",            value="250000.00",                            confidence=0.90, page=1),
                    ExtractedField(field_name="currency",          value="USD",                                  confidence=0.95, page=1),
                    ExtractedField(field_name="goods_description", value="Electronic Components - PCB Assemblies", confidence=0.85, page=1),
                    ExtractedField(field_name="quantity",          value="5000 PCS",                             confidence=0.88, page=1),
                    ExtractedField(field_name="beneficiary_name",  value="Shenzhen Lition Electronics Co Ltd",   confidence=0.85, page=1),
                    ExtractedField(field_name="applicant_name",    value="Adriatic Imports Sh.p.k.",             confidence=0.85, page=1),
                    ExtractedField(field_name="port_of_loading",   value="Shenzhen",                             confidence=0.88, page=1),
                    ExtractedField(field_name="port_of_discharge", value="Durres",                               confidence=0.88, page=1),
                ],
            ),
            ExtractedDocument(
                document_type=DocumentType.bill_of_lading,
                file="bill_of_lading.pdf",
                fields=[
                    ExtractedField(field_name="bl_number",         value="COSU2026060501",                       confidence=0.92, page=1),
                    ExtractedField(field_name="on_board_date",     value="05/06/2026",                           confidence=0.92, page=1),
                    ExtractedField(field_name="port_of_loading",   value="Shenzhen",                             confidence=0.88, page=1),
                    ExtractedField(field_name="port_of_discharge", value="Durres",                               confidence=0.88, page=1),
                    ExtractedField(field_name="goods_description", value="Electronic Components - PCB Assemblies", confidence=0.85, page=1),
                    ExtractedField(field_name="gross_weight",      value="12500 KGS",                            confidence=0.90, page=1),
                    ExtractedField(field_name="shipper",           value="Shenzhen Lition Electronics Co Ltd",   confidence=0.85, page=1),
                ],
            ),
            ExtractedDocument(
                document_type=DocumentType.packing_list,
                file="packing_list.pdf",
                fields=[
                    ExtractedField(field_name="goods_description", value="Electronic Components - PCB Assemblies", confidence=0.85, page=1),
                    ExtractedField(field_name="total_quantity",    value="5000 PCS",                             confidence=0.90, page=1),
                    ExtractedField(field_name="gross_weight",      value="12500 KGS",                            confidence=0.90, page=1),
                ],
            ),
            ExtractedDocument(
                document_type=DocumentType.letter_of_credit,
                file="lc.pdf",
                fields=[
                    ExtractedField(field_name="lc_number",             value="LC-2026-00099",                        confidence=0.95, page=1),
                    ExtractedField(field_name="amount",                value="250000.00",                            confidence=0.95, page=1),
                    ExtractedField(field_name="currency",              value="USD",                                  confidence=0.95, page=1),
                    ExtractedField(field_name="expiry_date",           value="2026-07-31",                           confidence=0.95, page=1),
                    ExtractedField(field_name="latest_shipment_date",  value="2026-07-10",                           confidence=0.92, page=1),
                    ExtractedField(field_name="beneficiary",           value="Shenzhen Lition Electronics Co Ltd",   confidence=0.88, page=1),
                    ExtractedField(field_name="applicant",             value="Adriatic Imports Sh.p.k.",             confidence=0.88, page=1),
                ],
            ),
        ],
    )


def sample_extracted_amount_over(bundle_id: str = "bundle_tolerance_03") -> ExtractedDocs:
    """Invoice amount 0.5 % over L/C – triggers discrepancy at tight tolerance."""
    base = sample_extracted_clean(bundle_id)
    for doc in base.documents:
        if doc.document_type == DocumentType.commercial_invoice:
            for f in doc.fields:
                if f.field_name == "amount":
                    f.value = "251250.00"   # +0.5 %
    return base


def sample_extracted_name_variation(bundle_id: str = "bundle_name_var_05") -> ExtractedDocs:
    """Beneficiary name on invoice slightly differs from L/C."""
    base = sample_extracted_clean(bundle_id)
    for doc in base.documents:
        if doc.document_type == DocumentType.commercial_invoice:
            for f in doc.fields:
                if f.field_name == "beneficiary_name":
                    f.value = "Shenzhen Lition Electronics Company Ltd"
    return base
