from __future__ import annotations
import csv
import re
from pathlib import Path
from typing import Optional

from app.config import settings
from app.schemas.common import BoundingBox, DocumentType
from app.schemas.extraction import ExtractedDocs, ExtractedDocument, ExtractedField
from app.state import PipelineState
from app.parsing.extraction_router import parse_document
from app.utils.io import write_model

LOW_CONFIDENCE_CUTOFF = 0.70


# â”€â”€â”€ Regex helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _first(pattern: str, text: str) -> Optional[str]:
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None


def _find_bbox(value: str, words: list[dict], page_num: int) -> Optional[BoundingBox]:
    if not value or not words:
        return None
    token = value.lower().split()[0]
    for w in words:
        if token in w["text"].lower():
            b = w["bbox"]
            return BoundingBox(x0=b[0], y0=b[1], x1=b[2], y1=b[3], page=page_num)
    return None


def _field(name: str, value: Optional[str], base_conf: float,
           page_num: int, words: list[dict]) -> ExtractedField:
    val = (value or "").strip()
    conf = round(base_conf if val else 0.20, 4)
    bbox = _find_bbox(val, words, page_num) if val else None
    low = conf < LOW_CONFIDENCE_CUTOFF
    return ExtractedField(
        field_name=name, value=val, confidence=conf, page=page_num,
        bounding_box=bbox, low_confidence=low, manual_review_required=low,
    )


# â”€â”€â”€ Per-document-type extractors â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _extract_invoice(pages: list[dict]) -> list[ExtractedField]:
    text = "\n".join(p["text"] for p in pages)
    words = [w for p in pages for w in p.get("words", [])]
    pn = pages[0]["page_num"] if pages else 1
    return [
        _field("invoice_number",    _first(r"invoice\s*(?:no|number|#)[:\s.]*([A-Z0-9\-/]+)", text), 0.92, pn, words),
        _field("invoice_date",      _first(r"invoice\s*date[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}-\d{2}-\d{2})", text), 0.90, pn, words),
        _field("amount",            _first(r"total\s*(?:amount|value)?[:\s]*(?:USD|EUR|GBP|[$â‚¬Â£])?\s*([\d,]+(?:\.\d+)?)", text), 0.90, pn, words),
        _field("currency",          _first(r"\b(USD|EUR|GBP|JPY|CHF|CNY)\b", text), 0.95, pn, words),
        _field("goods_description", _first(r"description\s*(?:of\s*goods)?[:\s]*([\w\s,\-.]+?)(?=\n|quantity|qty|amount|total)", text), 0.85, pn, words),
        _field("quantity",          _first(r"(?:total\s+)?quantity[:\s]*([\d,]+(?:\.\d+)?\s*(?:MT|KG|PCS|UNITS)?)", text), 0.88, pn, words),
        _field("beneficiary_name",  _first(r"(?:seller|beneficiary|exporter)[:\s]*([\w\s,\.]+?)(?=\n|address|tel|email)", text), 0.85, pn, words),
        _field("applicant_name",    _first(r"(?:buyer|applicant|importer)[:\s]*([\w\s,\.]+?)(?=\n|address|tel|email)", text), 0.85, pn, words),
        _field("port_of_loading",   _first(r"port\s*of\s*(?:loading|shipment)[:\s]*([\w\s,]+?)(?=\n|port\s*of\s*dis)", text), 0.88, pn, words),
        _field("port_of_discharge", _first(r"port\s*of\s*(?:discharge|destination)[:\s]*([\w\s,]+?)(?=\n|$)", text), 0.88, pn, words),
        _field("incoterms",         _first(r"\b(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\b", text), 0.95, pn, words),
    ]


def _extract_bol(pages: list[dict]) -> list[ExtractedField]:
    text = "\n".join(p["text"] for p in pages)
    words = [w for p in pages for w in p.get("words", [])]
    pn = pages[0]["page_num"] if pages else 1
    return [
        _field("bl_number",         _first(r"b/?l\s*(?:no|number|#)?[:\s.]*([A-Z0-9\-/]+)", text), 0.92, pn, words),
        _field("on_board_date",     _first(r"(?:on\s*board\s*date|shipped\s*on\s*board\s*date)[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}-\d{2}-\d{2})", text), 0.92, pn, words),
        _field("shipment_date",       _first(r"(?:on\s*board\s*date|shipped\s*on\s*board\s*date)[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}-\d{2}-\d{2})", text), 0.92, pn, words),
        _field("presentation_date",   _first(r"(?:presentation\s*date|presented\s*on)[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}-\d{2}-\d{2})", text), 0.90, pn, words),
        _field("partial_shipment",    _first(r"partial\s*shipment[:\s]*(YES|NO|TRUE|FALSE|ALLOWED|NOT\s*ALLOWED)", text), 0.90, pn, words),
        _field("port_of_loading",   _first(r"port\s*of\s*loading[:\s]*([\w\s,]+?)(?=\n|port\s*of\s*dis)", text), 0.88, pn, words),
        _field("port_of_discharge", _first(r"port\s*of\s*discharge[:\s]*([\w\s,]+?)(?=\n|$|vessel|date)", text), 0.88, pn, words),
        _field("goods_description", _first(r"description\s*of\s*goods?[:\s]*([\w\s,\-.]+?)(?=\n|gross|net|measurement)", text), 0.85, pn, words),
        _field("gross_weight",      _first(r"gross\s*weight[:\s]*([\d,]+(?:\.\d+)?\s*(?:KGS?|MT|LBS?)?)", text), 0.90, pn, words),
        _field("shipper",           _first(r"shipper[:\s]*([\w\s,\.]+?)(?=\n|consignee|notify)", text), 0.85, pn, words),
        _field("consignee",         _first(r"consignee[:\s]*([\w\s,\.]+?)(?=\n|notify|port)", text), 0.85, pn, words),
        _field("freight_terms",     _first(r"\b(FREIGHT\s*PREPAID|FREIGHT\s*COLLECT)\b", text), 0.95, pn, words),
    ]


def _extract_packing_list(pages: list[dict]) -> list[ExtractedField]:
    text = "\n".join(p["text"] for p in pages)
    words = [w for p in pages for w in p.get("words", [])]
    pn = pages[0]["page_num"] if pages else 1
    return [
        _field("goods_description", _first(r"description\s*(?:of\s*goods?)?[:\s]*([\w\s,\-.]+?)(?=\n|quantity|packages)", text), 0.85, pn, words),
        _field("total_quantity",    _first(r"total\s*quantity[:\s]*([\d,]+(?:\.\d+)?\s*(?:MT|KG|PCS|UNITS)?)", text), 0.90, pn, words),
        _field("gross_weight",      _first(r"gross\s*weight[:\s]*([\d,]+(?:\.\d+)?\s*(?:KGS?|MT|LBS?)?)", text), 0.90, pn, words),
        _field("net_weight",        _first(r"net\s*weight[:\s]*([\d,]+(?:\.\d+)?\s*(?:KGS?|MT|LBS?)?)", text), 0.88, pn, words),
        _field("exporter",          _first(r"(?:exporter|seller)[:\s]*([\w\s,\.]+?)(?=\n|importer|buyer|date)", text), 0.85, pn, words),
        _field("importer",          _first(r"(?:importer|buyer|consignee)[:\s]*([\w\s,\.]+?)(?=\n|date|packing)", text), 0.85, pn, words),
    ]


def _extract_cert_of_origin(pages: list[dict]) -> list[ExtractedField]:
    text = "\n".join(p["text"] for p in pages)
    words = [w for p in pages for w in p.get("words", [])]
    pn = pages[0]["page_num"] if pages else 1
    return [
        _field("country_of_origin", _first(r"country\s*of\s*origin[:\s]*([\w\s]+?)(?=\n|$|goods|description)", text), 0.92, pn, words),
        _field("exporter",          _first(r"(?:exporter|producer|manufacturer)[:\s]*([\w\s,\.]+?)(?=\n|country|consignee)", text), 0.85, pn, words),
        _field("goods_description", _first(r"description\s*(?:of\s*goods?)?[:\s]*([\w\s,\-.]+?)(?=\n|quantity|cert)", text), 0.85, pn, words),
        _field("quantity",          _first(r"quantity[:\s]*([\d,]+(?:\.\d+)?\s*(?:MT|KG|PCS|UNITS)?)", text), 0.88, pn, words),
    ]


def _extract_lc(pages: list[dict]) -> list[ExtractedField]:
    text = "\n".join(p["text"] for p in pages)
    words = [w for p in pages for w in p.get("words", [])]
    pn = pages[0]["page_num"] if pages else 1
    return [
        _field("lc_number",                _first(r"(?:documentary\s*credit\s*(?:no|number)?|l/?c\s*(?:no|number|#)?)[:\s.]*([A-Z0-9\-/]+)", text), 0.95, pn, words),
        _field("amount",                   _first(r"amount[:\s]*(?:USD|EUR|GBP|[$â‚¬Â£])?\s*([\d,]+(?:\.\d+)?)", text), 0.95, pn, words),
        _field("currency",                 _first(r"\b(USD|EUR|GBP|JPY|CHF|CNY)\b", text), 0.95, pn, words),
        _field("expiry_date",              _first(r"(?:expiry\s*date|valid\s*until)[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}-\d{2}-\d{2})", text), 0.95, pn, words),
        _field("latest_shipment_date",     _first(r"latest\s*(?:date\s*of\s*)?shipment[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}-\d{2}-\d{2})", text), 0.92, pn, words),
        _field("beneficiary",              _first(r"beneficiary[:\s]*([\w\s,\.]+?)(?=\n|amount|expiry|available)", text), 0.88, pn, words),
        _field("applicant",                _first(r"applicant[:\s]*([\w\s,\.]+?)(?=\n|beneficiary|amount)", text), 0.88, pn, words),
        _field("partial_shipment",         _first(r"partial\s*(?:shipments?)?[:\s]*(ALLOWED?|NOT\s*ALLOWED?|PERMITTED?|PROHIBITED?)", text), 0.92, pn, words),
        _field("transhipment",             _first(r"trans(?:hi)?pment[:\s]*(ALLOWED?|NOT\s*ALLOWED?|PERMITTED?|PROHIBITED?)", text), 0.92, pn, words),
        _field("presentation_period_days", _first(r"presentation\s*period[:\s]*within\s*(\d+)\s*days?", text), 0.90, pn, words),
    ]


def _extract_inspection_cert(pages: list[dict]) -> list[ExtractedField]:
    text = "\n".join(p["text"] for p in pages)
    words = [w for p in pages for w in p.get("words", [])]
    pn = pages[0]["page_num"] if pages else 1
    return [
        _field("cert_number",       _first(r"certificate\s*(?:no|number|#)?[:\s.]*([A-Z0-9\-/]+)", text), 0.90, pn, words),
        _field("inspection_date",   _first(r"(?:inspection\s+)?date[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}-\d{2}-\d{2})", text), 0.88, pn, words),
        _field("goods_description", _first(r"description\s*(?:of\s*goods?)?[:\s]*([\w\s,\-.]+?)(?=\n|quantity|result)", text), 0.85, pn, words),
        _field("inspection_result", _first(r"\b(PASSED?|FAILED?|APPROVED?|REJECTED?|SATISFACTORY)\b", text), 0.92, pn, words),
    ]


_EXTRACTORS = {
    DocumentType.commercial_invoice:     _extract_invoice,
    DocumentType.bill_of_lading:         _extract_bol,
    DocumentType.packing_list:           _extract_packing_list,
    DocumentType.certificate_of_origin:  _extract_cert_of_origin,
    DocumentType.letter_of_credit:       _extract_lc,
    DocumentType.inspection_certificate: _extract_inspection_cert,
}


# â”€â”€â”€ CSV export â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _write_csv(path: Path, docs: list[ExtractedDocument]) -> None:
    rows = [
        {
            "document_type": doc.document_type.value,
            "file": doc.file,
            "field_name": f.field_name,
            "value": f.value,
            "confidence": f.confidence,
            "page": f.page,
            "low_confidence": f.low_confidence,
            "manual_review_required": f.manual_review_required,
        }
        for doc in docs
        for f in doc.fields
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        fieldnames = ["document_type", "file", "field_name", "value", "confidence",
                      "page", "low_confidence", "manual_review_required"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# â”€â”€â”€ Public interface (P1 contract: run(state) -> state) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def run(state: PipelineState) -> PipelineState:
    """Agent B: parse every document in the bundle and extract structured fields."""
    if state.context is None:
        state.warnings.append("agent_b: no context packet; skipping extraction")
        return state

    extracted_docs = []
    for doc_ref in state.context.documents:
        file_path = state.bundle_path / doc_ref.file
        parsed = parse_document(file_path)

        if parsed.get("error") or not parsed["pages"]:
            extracted_docs.append(ExtractedDocument(
                document_type=doc_ref.type,
                file=doc_ref.file,
                fields=[],
            ))
            state.warnings.append(f"agent_b: synthetic fallback for {doc_ref.file}: {parsed.get('error')}")
            continue

        extractor = _EXTRACTORS.get(doc_ref.type)
        fields = extractor(parsed["pages"]) if extractor else []

        # OCR path introduces recognition uncertainty â€” apply confidence penalty
        if parsed["path_taken"] == "ocr":
            penalised = []
            for f in fields:
                new_conf = round(f.confidence * 0.80, 4)
                low = new_conf < LOW_CONFIDENCE_CUTOFF
                penalised.append(f.model_copy(update={
                    "confidence": new_conf,
                    "low_confidence": low,
                    "manual_review_required": low,
                }))
            fields = penalised

        if settings.USE_LLM:
            from app.llm.extractor import retry_field
            page_text = "\n".join(p["text"] for p in parsed["pages"])
            fields = [retry_field(f.field_name, page_text, f) for f in fields]

        low_conf = [f for f in fields if f.low_confidence]
        if len(fields) and len(low_conf) > len(fields) * 0.5:
            state.warnings.append(
                f"agent_b: {doc_ref.file} â€“ {len(low_conf)}/{len(fields)} fields low-confidence"
                f" (path={parsed['path_taken']})"
            )

        extracted_docs.append(ExtractedDocument(
            document_type=doc_ref.type,
            file=doc_ref.file,
            fields=fields,
        ))

    result = ExtractedDocs(bundle_id=state.bundle_id, documents=extracted_docs)
    state.extracted = result

    write_model(state.run_dir / "extracted_docs.json", result)
    _write_csv(state.run_dir / "extracted_docs.csv", extracted_docs)

    return state

