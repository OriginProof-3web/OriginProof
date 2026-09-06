from __future__ import annotations

import json
from pathlib import Path

from originproof_core import (
    CardPaymentNotice,
    CardPaymentNoticeCandidate,
    SignedProofEnvelope,
    VerificationResult,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "packages" / "schemas" / "generated" / "json"
SCHEMAS = {
    "card-payment-notice.schema.json": CardPaymentNotice,
    "card-payment-notice-candidate.schema.json": CardPaymentNoticeCandidate,
    "signed-proof-envelope.schema.json": SignedProofEnvelope,
    "verification-result.schema.json": VerificationResult,
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, model in SCHEMAS.items():
        schema = model.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        (OUTPUT_DIR / filename).write_text(
            json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(f"Generated {len(SCHEMAS)} JSON Schemas in {OUTPUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
