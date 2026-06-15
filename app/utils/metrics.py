from app.schemas.decision import Metrics


def compute_metrics(
    bundle_id: str,
    run_id: str,
    extracted,
    findings: list,
    decision: str,
    processing_time: float,
) -> Metrics:
    total_fields = sum(len(d.fields) for d in extracted.documents) if extracted else 0
    low_conf = sum(
        1 for d in extracted.documents for f in d.fields if f.low_confidence
    ) if extracted else 0
    accuracy = 1.0 - (low_conf / total_fields) if total_fields > 0 else 1.0
    major_count = sum(1 for f in findings if f.severity == "major")
    discrepancy_rate = major_count / len(findings) if findings else 0.0

    return Metrics(
        bundle_id=bundle_id,
        run_id=run_id,
        total_documents=len(extracted.documents) if extracted else 0,
        total_fields_extracted=total_fields,
        low_confidence_fields=low_conf,
        extraction_accuracy=round(accuracy, 4),
        discrepancy_rate=round(discrepancy_rate, 4),
        processing_time_seconds=round(processing_time, 3),
        decision=decision,
    )
