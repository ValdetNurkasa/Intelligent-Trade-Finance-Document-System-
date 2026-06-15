import yaml
from pathlib import Path


def load_policy(base_path: Path = Path("config/policy_pack.yaml"), region: str = None) -> dict:
    with open(base_path) as f:
        policy = yaml.safe_load(f)

    if region:
        regional_path = Path(f"config/regional/{region}_policy.yaml")
        if regional_path.exists():
            with open(regional_path) as f:
                regional = yaml.safe_load(f)
            policy.update(regional)

    return policy
