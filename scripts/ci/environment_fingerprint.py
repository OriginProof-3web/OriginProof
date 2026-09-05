from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build" / "environment_fingerprint.json"


def command(*args: str) -> str:
    if shutil.which(args[0]) is None:
        return "NOT_INSTALLED"
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return f"UNAVAILABLE_EXIT_{result.returncode}"
    output = result.stdout.strip().splitlines()
    return output[0] if output else "OK"


def digest(path: Path) -> str:
    if not path.is_file():
        return "MISSING"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(paths: list[Path]) -> str:
    hasher = hashlib.sha256()
    existing = sorted(
        path
        for root in paths
        if root.exists()
        for path in root.rglob("*")
        if path.is_file()
    )
    if not existing:
        return "MISSING"
    for path in existing:
        hasher.update(path.relative_to(ROOT).as_posix().encode())
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def main() -> int:
    fingerprint = {
        "comparable": {
            "git_sha": command("git", "rev-parse", "HEAD"),
            "docker": command("docker", "--version"),
            "compose": command("docker", "compose", "version"),
            "python": command("python", "--version"),
            "uv": command("uv", "--version"),
            "node": command("node", "--version"),
            "pnpm": command("pnpm", "--version"),
            "forge": command("forge", "--version"),
            "lockfiles": {
                "uv.lock": digest(ROOT / "uv.lock"),
                "pnpm-lock.yaml": digest(ROOT / "pnpm-lock.yaml"),
                "contract_dependencies": digest(ROOT / "packages/contracts/dependencies.lock"),
            },
            "schema_tree": tree_digest(
                [ROOT / "packages/schemas", ROOT / "packages/python/originproof_core"]
            ),
            "abi_tree": tree_digest([ROOT / "packages/contracts/abi"]),
        },
        "informational": {"host_platform": platform.platform()},
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(fingerprint, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT.relative_to(ROOT))
    print(json.dumps(fingerprint, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
