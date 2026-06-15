from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from app.schemas.context import ContextPacket
from app.schemas.extraction import ExtractedDocs
from app.schemas.ucp import UCPResult
from app.schemas.matching import MatchResult
from app.schemas.sanctions import SanctionsScreen
from app.schemas.decision import FinalDecision


class PipelineState(BaseModel):
    bundle_id: str
    bundle_path: Path
    run_dir: Path
    context: Optional[ContextPacket] = None
    extracted: Optional[ExtractedDocs] = None
    ucp_result: Optional[UCPResult] = None
    match_result: Optional[MatchResult] = None
    sanctions: Optional[SanctionsScreen] = None
    final_decision: Optional[FinalDecision] = None
    errors: list[str] = []
    warnings: list[str] = []

    model_config = {"arbitrary_types_allowed": True}
