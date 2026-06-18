from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
import tempfile
import zipfile

from app.pipeline import run_pipeline
from app.state import PipelineState

app = FastAPI(title="ITFDS API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
async def run(bundle: UploadFile = File(...)):
    if not bundle.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Bundle must be a .zip file")

    tmp_root = Path(tempfile.mkdtemp())
    zip_path = tmp_root / bundle.filename
    zip_path.write_bytes(await bundle.read())

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(tmp_root / "bundle")

    bundle_path = tmp_root / "bundle"
    subdirs = [p for p in bundle_path.iterdir() if p.is_dir()]
    if subdirs:
        bundle_path = subdirs[0]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = Path("runs") / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    bundle_id = bundle_path.name or bundle.filename.replace(".zip", "")

    state = PipelineState(
        bundle_id=bundle_id,
        bundle_path=bundle_path,
        run_dir=run_dir,
    )

    state = run_pipeline(state)

    decision = state.final_decision.decision if state.final_decision else "PENDING"

    return {
        "bundle_id": bundle_id,
        "decision": decision,
        "run_dir": str(run_dir),
        "findings_summary": state.final_decision.findings_summary if state.final_decision else None,
    }
