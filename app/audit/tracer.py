from datetime import datetime, timezone
from pathlib import Path
from app.utils.io import write_json


class Tracer:
    def __init__(self, run_dir: Path, bundle_id: str, bundle_path: Path):
        self.run_dir = run_dir
        self.bundle_id = bundle_id
        self.bundle_path = str(bundle_path)
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.events = []

    def log(self, agent: str, event: str, detail: dict = None):
        self.events.append({
            "agent": agent,
            "event": event,
            "detail": detail or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def save(self, decision: str = "PENDING"):
        write_json(self.run_dir / "run_metadata.json", {
            "bundle_id": self.bundle_id,
            "bundle_path": self.bundle_path,
            "started_at": self.started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "decision": decision,
            "events": self.events,
        })
