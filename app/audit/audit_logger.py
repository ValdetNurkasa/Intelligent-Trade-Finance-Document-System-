from pathlib import Path
from app.utils.io import write_text


def write_audit_log(run_dir: Path, bundle_id: str, events: list, decision: str):
    lines = [
        f"# Audit Log - {bundle_id}",
        "",
        f"**Final Decision:** {decision}",
        "",
        "## Event Trace",
        "",
    ]
    for e in events:
        lines.append(f"- [{e['agent']}] {e['event']} - {e['timestamp']}")
        if e.get("detail"):
            for k, v in e["detail"].items():
                lines.append(f"  - {k}: {v}")

    write_text(run_dir / "audit_log.md", "\n".join(lines))
