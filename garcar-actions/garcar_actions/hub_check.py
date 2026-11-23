"""Port of the hub structure-check job, with strict JSON failure reporting."""
import json
import os
from pathlib import Path


REQUIRED = ("README.md", "Makefile", "docker-compose.yml", "SYSTEMS-INVENTORY.json", ".github/workflows/ci.yml")
EXCLUDED = {".git", "node_modules", ".venv", "venv", "__pycache__", "data"}


def validate(root):
    root = Path(root).resolve()
    errors = []
    for name in REQUIRED:
        path = root / name
        if not path.is_file() or not path.resolve().is_relative_to(root):
            errors.append(f"Missing or external required file: {name}")
    checked = 0
    for directory, names, files in os.walk(root, followlinks=False):
        names[:] = [name for name in names if name not in EXCLUDED and not (Path(directory) / name).is_symlink()]
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix != ".json" or path.is_symlink():
                continue
            try:
                with path.open(encoding="utf-8") as source:
                    json.load(source)
                checked += 1
            except (OSError, ValueError) as exc:
                errors.append(f"Invalid JSON {path.relative_to(root)}: {exc}")
    inventory = root / "SYSTEMS-INVENTORY.json"
    if inventory.is_file() and inventory.resolve().is_relative_to(root):
        try:
            data = json.loads(inventory.read_text(encoding="utf-8"))
            categories = data.get("categories", {})
            summary = {"categories": len(categories), "declared_systems": sum(len(v) for v in categories.values()),
                       "declared_repositories": data.get("overview", {}).get("total_repositories", 0)}
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            errors.append(f"Invalid inventory structure: {exc}")
            summary = {}
    else:
        summary = {}
    return {"valid": not errors, "json_files_checked": checked, "errors": errors, "inventory_declarations": summary}


if __name__ == "__main__":
    report = validate(Path.cwd())
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["valid"] else 1)
