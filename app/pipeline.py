from pathlib import Path
from app.state import PipelineState
from app.agents.agent_a_intake import run as run_a
from app.agents.agent_b_extraction import run as run_b
from app.agents.agent_c_ucp import run as run_c
from app.agents.agent_d_matching import run as run_d
from app.agents.agent_e_sanctions import run as run_e
from app.agents.agent_h_orchestrator import run as run_h


def run_pipeline(state: PipelineState) -> PipelineState:
    state = run_a(state)
    state = run_b(state)
    state = run_c(state)
    state = run_d(state)
    state = run_e(state)
    state = run_h(state)
    return state
