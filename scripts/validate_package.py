from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover - environments without the extra
    jsonschema = None


def check(instance: Path, schema: Path, label: str) -> list[str]:
    if not schema.exists():
        return [f"{label}: cached schema is missing ({schema})"]
    if jsonschema is None:
        return []
    data = json.loads(instance.read_text(encoding="utf-8"))
    schema_data = json.loads(schema.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema_data)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    return [
        f"{label}: {'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
        for error in errors
    ]


def validate(root: Path, schemas: Path) -> list[str]:
    issues: list[str] = []
    for name in ("plugin.json", "mcp.json"):
        instance = root / name
        if instance.exists():
            issues += check(instance, schemas / (name[: -len(".json")] + ".schema.json"), name)
    return issues


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    schemas = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else root / "dist" / "_schema"
    issues = validate(root, schemas)
    if issues:
        print("\n".join(issues), file=sys.stderr)
        return 1
    print(f"Package validation passed: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
