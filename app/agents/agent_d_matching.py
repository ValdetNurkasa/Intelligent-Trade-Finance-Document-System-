from app.state import PipelineState
from app.rules.matching_rules import run_matching
from app.tools.policy_loader import load_policy
from app.utils.io import write_model


def run(state: PipelineState) -> PipelineState:
    if state.context is None or state.extracted is None:
        state.warnings.append("agent_d: missing context or extracted docs; skipping matching")
        return state

    policy = load_policy()
    tolerance_pct = policy.get("tolerance_percent", state.context.flags.tolerance_percent)

    if state.tracer:
        state.tracer.log("D", "matching complete", {"tolerance_pct": tolerance_pct})

    result = run_matching(state.extracted, tolerance_pct=tolerance_pct)
    state.match_result = result
    write_model(state.run_dir / "match_result.json", result)
    return state
