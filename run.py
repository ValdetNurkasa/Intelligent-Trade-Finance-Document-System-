#!/usr/bin/env python3
import argparse
from datetime import datetime
from pathlib import Path

from agents.agent_a import run as run_agent_a
from agents.agent_b import run as run_agent_b
from agents.agent_c import run as run_agent_c
from agents.agent_d import run as run_agent_d
from agents.agent_e import run as run_agent_e
from agents.agent_h import run as run_agent_h


def create_run_dir() -> Path:
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
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

    run_dir = create_run_dir()
    print(f"[ITFDS] Run: {run_dir}  |  Bundle: {bundle_path}")

    if args.dry_run:
        print("[ITFDS] Dry run complete.")
        return

    context      = run_agent_a(bundle_path, run_dir)
    extracted    = run_agent_b(context, run_dir)
    ucp_result   = run_agent_c(context, extracted, run_dir)
    match_result = run_agent_d(context, extracted, run_dir)
    sanctions    = run_agent_e(context, run_dir)
    final        = run_agent_h(context, ucp_result, match_result, sanctions, run_dir)

    print(f"\n[ITFDS] DECISION: {final.get('decision', 'PENDING')}")
    print(f"[ITFDS] Artifacts -> {run_dir}\n")


if __name__ == "__main__":
    main()
