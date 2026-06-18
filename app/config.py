import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    USE_LLM: bool = os.getenv("USE_LLM", "false").lower() == "true"
    OCR_QUALITY_CUTOFF: float = float(os.getenv("OCR_QUALITY_CUTOFF", "0.75"))
    LOW_CONFIDENCE_CUTOFF: float = float(os.getenv("LOW_CONFIDENCE_CUTOFF", "0.75"))
    POLICY_PATH: Path = Path("config/policy_pack.yaml")
    RUNS_DIR: Path = Path("runs")


settings = Settings()
