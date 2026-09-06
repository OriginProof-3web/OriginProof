from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "mvp"
OUTPUT = ROOT / "build" / "seed_manifest.json"


def read_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def main() -> int:
    valid = read_fixture("card_notice_valid.json")
    tampered = read_fixture("card_notice_amount_tampered.json")
    if valid["proof_id"] != tampered["proof_id"]:
        raise SystemExit("fixtures must use the same proof_id")
    if valid["amount_minor"] == tampered["amount_minor"]:
        raise SystemExit("tampered fixture must change amount_minor")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {
                "issuer": "Origin Mock Bank",
                "proof_id": valid["proof_id"],
                "fixtures": ["card_notice_valid.json", "card_notice_amount_tampered.json"],
                "source": "synthetic",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
