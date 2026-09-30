from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_FILES = (".env", "pyproject.toml", "uv.lock", "pnpm-lock.yaml", "docker-compose.yml")
REQUIRED_COMMANDS = ("docker", "uv", "node", "pnpm")


def main() -> int:
    missing_files = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    missing_commands = [name for name in REQUIRED_COMMANDS if shutil.which(name) is None]
    if missing_files or missing_commands:
        print("Environment check failed:")
        for name in missing_files:
            print(f"- missing file: {name}")
        for name in missing_commands:
            print(f"- missing command: {name}")
        return 1
    try:
        subprocess.run(
            ["docker", "compose", "version"], check=True, capture_output=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        print("Environment check failed: Docker Compose is unavailable.")
        return 1
    print("Environment check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
