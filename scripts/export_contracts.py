"""Export/check the actual API model's version-one event contract."""
import argparse
import json
from pathlib import Path

from governloom.monitoring import RuntimeEvent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / "docs/contracts/runtime-event-v1.schema.json"
    schema = RuntimeEvent.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    content = json.dumps(schema, indent=2) + "\n"
    if options.check:
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            raise SystemExit("Event contract changed: regenerate and review compatibility")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
