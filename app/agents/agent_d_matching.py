from app.state import PipelineState
from app.rules.matching_rules import run_matching
from app.utils.io import write_model


def run(state: PipelineState) -> PipelineState:
    """Agent D: cross-document consistency matching."""
    if state.context is None or state.extracted is None:
        state.warnings.append("agent_d: missing context or extracted docs; skipping matching")
        return state

    tolerance_pct = state.context.flags.tolerance_percent
    result = run_matching(state.extracted, tolerance_pct=tolerance_pct)
    state.match_result = result

    write_model(state.run_dir / "match_result.json", result)
    return state
