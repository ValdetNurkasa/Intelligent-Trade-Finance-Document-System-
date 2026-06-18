import yaml
from pathlib import Path

from app.state import PipelineState
from app.schemas.context import (
    ContextPacket,
    Party,
    Vessel,
    Ports,
    LCFlags,
    DocumentRef,
    EvidenceItem,
)
from app.schemas.common import DocumentType, RiskLevel
from app.parsing.classifier import classify
from app.utils.io import write_model


HIGH_RISK_COUNTRIES = {"IR", "KP", "SY", "CU", "RU", "BY", "MM"}
HIGH_RISK_FLAG_STATES = {"KM", "PW", "SL", "TZ", "MH"}

REQUIRED_DOCUMENTS = {
    DocumentType.letter_of_credit,
    DocumentType.bill_of_lading,
    DocumentType.commercial_invoice,
}


def load_manifest(bundle_path: Path) -> dict:
    manifest_path = bundle_path / "manifest.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.yaml not found in {bundle_path}")
    with open(manifest_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_party(data: dict) -> Party:
    return Party(
        name=data.get("name", ""),
        address=data.get("address", ""),
        swift=data.get("swift"),
        country=data.get("country"),
    )


def build_document_refs(manifest: dict, bundle_path: Path) -> list[DocumentRef]:
    refs = []
    for doc in manifest.get("documents", []):
        raw_type = doc.get("type", "")
        file_name = doc.get("file", "")
        file_path = bundle_path / file_name

        try:
            doc_type = DocumentType(raw_type)
        except ValueError:
            doc_type = classify(file_path)

        refs.append(
            DocumentRef(
                type=doc_type,
                file=file_name,
                reference=doc.get("reference"),
                date=doc.get("date"),
            )
        )
    return refs


def build_evidence_index(manifest: dict) -> dict[str, EvidenceItem]:
    index = {}
    for doc in manifest.get("documents", []):
        doc_type = doc.get("type", "")
        file_name = doc.get("file", "")

        if doc.get("reference"):
            index[f"{doc_type}.reference"] = EvidenceItem(
                file=file_name,
                page=1,
                field="reference",
                value=doc["reference"],
            )
        if doc.get("date"):
            index[f"{doc_type}.date"] = EvidenceItem(
                file=file_name,
                page=1,
                field="date",
                value=doc["date"],
            )

    lc_file = next(
        (d["file"] for d in manifest.get("documents", [])
         if d.get("type") == "letter_of_credit"),
        "",
    )
    for field in ["lc_number", "currency", "amount", "expiry_date"]:
        value = manifest.get(field)
        if value:
            index[f"letter_of_credit.{field}"] = EvidenceItem(
                file=lc_file,
                page=1,
                field=field,
                value=str(value),
            )

    return index


def detect_risk_flags(manifest: dict, doc_refs: list[DocumentRef]) -> tuple[list[str], RiskLevel]:
    flags = []
    level = RiskLevel.low

    vessel = manifest.get("vessel", {})
    flag_state = vessel.get("flag_state", "")
    if flag_state in HIGH_RISK_FLAG_STATES:
        flags.append(f"High-risk vessel flag state: {flag_state}")
        level = RiskLevel.high

    for party_key in ["applicant", "beneficiary"]:
        party = manifest.get(party_key, {})
        country = party.get("country", "")
        if country in HIGH_RISK_COUNTRIES:
            flags.append(f"High-risk country for {party_key}: {country}")
            level = RiskLevel.high

    present_types = {ref.type for ref in doc_refs}
    missing = REQUIRED_DOCUMENTS - present_types
    if missing:
        flags.append(f"Missing required documents: {', '.join(t.value for t in missing)}")
        if level == RiskLevel.low:
            level = RiskLevel.medium

    return flags, level


def run(state: PipelineState) -> PipelineState:
    if state.tracer:
        state.tracer.log("A", "intake started")

    manifest = load_manifest(state.bundle_path)

    doc_refs = build_document_refs(manifest, state.bundle_path)
    evidence_index = build_evidence_index(manifest)
    risk_flags, risk_level = detect_risk_flags(manifest, doc_refs)

    vessel_data = manifest.get("vessel", {})
    ports_data = manifest.get("ports", {})
    flags_data = manifest.get("flags", {})

    context = ContextPacket(
        bundle_id=state.bundle_id,
        lc_number=manifest.get("lc_number", ""),
        currency=manifest.get("currency", "USD"),
        amount=float(manifest.get("amount", 0)),
        expiry_date=manifest.get("expiry_date", ""),
        latest_shipment_date=manifest.get("latest_shipment_date"),
        presentation_period_days=int(manifest.get("presentation_period_days", 21)),
        incoterms=manifest.get("incoterms"),
        ucp_version=manifest.get("ucp_version"),
        applicant=build_party(manifest.get("applicant", {})),
        beneficiary=build_party(manifest.get("beneficiary", {})),
        issuing_bank=build_party(manifest.get("issuing_bank", {})),
        advising_bank=build_party(manifest.get("advising_bank", {})),
        vessel=Vessel(
            name=vessel_data.get("name", ""),
            imo=vessel_data.get("imo", ""),
            flag_state=vessel_data.get("flag_state", ""),
            voyage=vessel_data.get("voyage"),
        ),
        ports=Ports(
            loading=ports_data.get("loading", ""),
            discharge=ports_data.get("discharge", ""),
        ),
        flags=LCFlags(
            partial_shipment_allowed=flags_data.get("partial_shipment_allowed", False),
            transhipment_allowed=flags_data.get("transhipment_allowed", False),
            tolerance_percent=float(flags_data.get("tolerance_percent", 5.0)),
        ),
        documents=doc_refs,
        evidence_index=evidence_index,
        risk_flags=risk_flags,
        risk_level=risk_level,
    )

    write_model(state.run_dir / "context_packet.json", context)

    state.context = context

    if state.tracer:
        state.tracer.log("A", "intake complete", {
            "documents": len(doc_refs),
            "risk_level": risk_level.value,
            "risk_flags": len(risk_flags),
        })

    return state
