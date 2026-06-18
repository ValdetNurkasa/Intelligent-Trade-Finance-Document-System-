import time
from datetime import datetime, timezone
from app.state import PipelineState
from app.agents.agent_a_intake import run as run_a
from app.agents.agent_b_extraction import run as run_b
from app.agents.agent_c_ucp import run as run_c
from app.agents.agent_d_matching import run as run_d
from app.agents.agent_e_sanctions import run as run_e
from app.agents.agent_h_orchestrator import run as run_h
from app.schemas.decision import FinalDecision
from app.utils.io import write_model
from app.utils.metrics import compute_metrics
from app.rules.discrepancy_rules import collect_findings


def _freeze_for_sanctions(state: PipelineState) -> PipelineState:
    if state.tracer:
        state.tracer.log("PIPELINE", "sanctions freeze triggered", {
            "hits": len(state.sanctions.hits) if state.sanctions else 0,
        })

    decision = FinalDecision(
        bundle_id=state.bundle_id,
        decision="REFUSE",
        decision_basis="Sanctions hit detected - processing frozen immediately.",
        findings_summary={
            "major": 0,
            "minor": 0,
            "warnings": 0,
            "sanctions_hits": len(state.sanctions.hits) if state.sanctions else 1,
        },
        finding_ids=[],
        swift_message_type="MT752",
        audit_trail=str(state.run_dir / "audit_log.md"),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    write_model(state.run_dir / "final_decision.json", decision)
    state.final_decision = decision
    return state


def _has_sanctions_hit(state: PipelineState) -> bool:
    return (
        state.sanctions is not None
        and state.sanctions.freeze_processing
    )


def _has_low_confidence(state: PipelineState) -> bool:
    if state.extracted is None:
        return False
    for doc in state.extracted.documents:
        for field in doc.fields:
            if field.low_confidence:
                return True
    return False


def _write_metrics(state: PipelineState, run_id: str, processing_time: float):
    findings = collect_findings(state.ucp_result, state.match_result, state.sanctions)
    decision = state.final_decision.decision if state.final_decision else "PENDING"
    metrics = compute_metrics(
        bundle_id=state.bundle_id,
        run_id=run_id,
        extracted=state.extracted,
        findings=findings,
        decision=decision,
        processing_time=processing_time,
    )
    write_model(state.run_dir / "metrics.json", metrics)


def run_pipeline(state: PipelineState) -> PipelineState:
    start_time = time.time()
    run_id = state.run_dir.name

    if state.tracer:
        state.tracer.log("A", "starting")
    state = run_a(state)

    if state.tracer:
        state.tracer.log("B", "starting")
    state = run_b(state)

    if _has_low_confidence(state):
        state.warnings.append("One or more fields have low extraction confidence and require manual review.")
        if state.tracer:
            state.tracer.log("PIPELINE", "low confidence fields detected - flagged for manual review")

    if state.tracer:
        state.tracer.log("C", "starting")
    state = run_c(state)

    if state.tracer:
        state.tracer.log("D", "starting")
    state = run_d(state)

    if state.tracer:
        state.tracer.log("E", "starting")
    state = run_e(state)

    if _has_sanctions_hit(state):
        state = _freeze_for_sanctions(state)
        _write_metrics(state, run_id, time.time() - start_time)
        return state

    if state.tracer:
        state.tracer.log("H", "starting")
    state = run_h(state)

    _write_metrics(state, run_id, time.time() - start_time)
    return state
