import hashlib


def make_finding_id(agent: str, rule: str, field: str, value: str) -> str:
    raw = f"{agent}:{rule}:{field}:{value}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def make_run_id(bundle_id: str, timestamp: str) -> str:
    raw = f"{bundle_id}:{timestamp}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]
