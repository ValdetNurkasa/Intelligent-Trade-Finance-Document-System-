from app.state import PipelineState
from app.rules.ucp600 import run_ucp_checks
from app.utils.io import write_model


def run(state: PipelineState) -> PipelineState:
    if state.context is None or state.extracted is None:
        state.warnings.append("agent_c: missing context or extracted docs; skipping UCP checks")
        return state

    result = run_ucp_checks(state.context, state.extracted, agent="agent_c")
    state.ucp_result = result
    write_model(state.run_dir / "ucp_result.json", result)
    return state
