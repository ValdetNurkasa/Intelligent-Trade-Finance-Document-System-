from datetime import datetime
from pathlib import Path
from app.utils.io import write_json


class Tracer:
    def __init__(self, run_dir: Path, bundle_id: str):
        self.run_dir = run_dir
        self.bundle_id = bundle_id
        self.events = []

    def log(self, agent: str, event: str, detail: dict = None):
        self.events.append({
            "agent": agent,
            "event": event,
            "detail": detail or {},
            "timestamp": datetime.utcnow().isoformat(),
        })

    def save(self):
        write_json(self.run_dir / "run_metadata.json", {
            "bundle_id": self.bundle_id,
            "events": self.events,
        })
