from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "repo_structure_manifest.json"
PROHIBITED_TOP_LEVEL = {"src2", "new", "temp", "final"}


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors: list[str] = []

    for name in manifest["required_top_level"]:
        if not (ROOT / name).is_dir():
            errors.append(f"missing directory: {name}")

    for name in manifest["required_agent_files"]:
        if not (ROOT / name).is_file():
            errors.append(f"missing instruction file: {name}")

    present = {path.name for path in ROOT.iterdir() if path.is_dir()}
    for name in sorted(present & PROHIBITED_TOP_LEVEL):
        errors.append(f"prohibited top-level directory: {name}")

    if errors:
        print("Repository structure validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Repository structure is valid: {manifest['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
