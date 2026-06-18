from app.state import PipelineState
from app.rules.sanctions_lists import screen
from app.tools.policy_loader import load_policy
from app.utils.io import write_model


def run(state: PipelineState) -> PipelineState:
    if state.context is None:
        state.warnings.append("agent_e: missing context; skipping sanctions screening")
        return state

    policy = load_policy()
    result = screen(state.context, policy)
    state.sanctions = result
    write_model(state.run_dir / "sanctions_screen.json", result)
    return state
