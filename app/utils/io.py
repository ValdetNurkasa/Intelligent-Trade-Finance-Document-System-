import json
from pathlib import Path
from pydantic import BaseModel


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)


def read_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_model(path: Path, model: BaseModel) -> None:
    write_json(path, json.loads(model.model_dump_json()))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
