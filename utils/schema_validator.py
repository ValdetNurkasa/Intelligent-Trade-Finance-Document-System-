import json
from pathlib import Path
import jsonschema


def load_schema(schema_name: str) -> dict:
    schema_path = Path("schemas") / f"{schema_name}.schema.json"
    with open(schema_path) as f:
        return json.load(f)


def validate(data: dict, schema_name: str) -> bool:
    schema = load_schema(schema_name)
    jsonschema.validate(instance=data, schema=schema)
    return True
