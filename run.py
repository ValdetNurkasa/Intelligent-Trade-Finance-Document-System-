#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone
from pathlib import Path

from app.pipeline import run_pipeline
from app.state import PipelineState
from app.audit.tracer import Tracer
from app.audit.audit_logger import write_audit_log
from app.reports.report_builder import write_run_report


def create_run_dir(bundle_id: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{timestamp}"
    run_dir = Path("runs") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def main():
    parser = argparse.ArgumentParser(description="ITFDS Pipeline Runner")
    parser.add_argument("--bundle", required=True, help="Path to trade bundle folder")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    bundle_path = Path(args.bundle)
    if not bundle_path.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")

    bundle_id = bundle_path.name
    run_dir = create_run_dir(bundle_id)

    print(f"[ITFDS] Run: {run_dir}  |  Bundle: {bundle_path}")

    if args.dry_run:
        print("[ITFDS] Dry run complete.")
        return

    tracer = Tracer(run_dir=run_dir, bundle_id=bundle_id, bundle_path=bundle_path)
    tracer.log("PIPELINE", "started", {"bundle": str(bundle_path)})

    state = PipelineState(
        bundle_id=bundle_id,
        bundle_path=bundle_path,
        run_dir=run_dir,
        tracer=tracer,
    )

    state = run_pipeline(state)

    decision = state.final_decision.decision if state.final_decision else "PENDING"

    tracer.log("PIPELINE", "completed", {"decision": decision})
    tracer.save(decision=decision)
    write_audit_log(
        run_dir=run_dir,
        bundle_id=bundle_id,
        events=tracer.events,
        decision=decision,
    )
    write_run_report(state)

    print(f"\n[ITFDS] DECISION: {decision}")
    print(f"[ITFDS] Artifacts -> {run_dir}\n")


if __name__ == "__main__":
    main()
