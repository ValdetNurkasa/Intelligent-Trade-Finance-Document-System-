from app.state import PipelineState
from app.tools.policy_loader import load_policy
from app.rules.decision_rules import decide, build_posting_payload
from app.rules.discrepancy_rules import collect_findings
from app.rules.swift_draft import generate_swift, generate_discrepancies_md
from app.utils.io import write_model, write_text


def run(state: PipelineState, timestamp: str = "") -> PipelineState:
    if state.context is None:
        state.warnings.append("agent_h: missing context; skipping decision")
        return state

    policy = load_policy()
    decision = decide(
        state.context,
        state.ucp_result,
        state.match_result,
        state.sanctions,
        policy,
        timestamp=timestamp,
    )
    state.final_decision = decision

    findings = collect_findings(state.ucp_result, state.match_result, state.sanctions)
    posting = build_posting_payload(state.context, decision)
    swift = generate_swift(state.context, decision)
    discrepancies = generate_discrepancies_md(state.context, decision, findings)

    write_model(state.run_dir / "final_decision.json", decision)
    write_model(state.run_dir / "posting_payload.json", posting)
    write_text(state.run_dir / "swift_draft.txt", swift)
    write_text(state.run_dir / "discrepancies.md", discrepancies)
    return state
