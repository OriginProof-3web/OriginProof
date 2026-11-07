"""D's W3 core cases reuse C's signed vectors; never create keys or edit Golden."""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build_cases():
    profiles, cases = {}, []
    for kind, fields, changed_field, changed_value in (
        ("payment_request", ("amount_minor", "currency", "target_hash"), "amount_minor", 154001),
        (
            "official_document",
            ("institution_code", "document_type", "document_number", "version"),
            "document_number",
            "SYNTHETIC-CHANGED",
        ),
    ):
        path = ROOT / "fixtures/golden" / f"{kind}_signing_v2.json"
        vector = json.loads(path.read_text())
        envelope = vector["envelope"]
        profiles[kind] = {
            "golden": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "issuer_id": envelope["issuer_id"],
            "proof_type": envelope["proof_type"],
            "comparison_fields": list(fields),
        }

        def add(
            label,
            changes=None,
            status="VERIFIED",
            scope="FULL_COMPARISON",
            reasons=(),
            checks=None,
            layer="core",
            profile=kind,
        ):
            expected = (
                {"decision": "SCHEMA_REJECTED"}
                if layer == "input_model"
                else {
                    "verification_status": status,
                    "scope": scope,
                    "reason_codes": list(reasons),
                    "checks": checks or {},
                }
            )
            cases.append(
                {
                    "id": f"w3_{profile}_{label}",
                    "profile": profile,
                    "layer": layer,
                    "changes": changes or {},
                    "expected": expected,
                    "basis": "development_plan §15.4 W3-D1/D2; ADR 0001 §1/4/6",
                    "live_execution_status": "NOT_RUN",
                }
            )

        add("normal", checks={"signature": "PASS", "candidate_match": "PASS"})
        add(
            "id_only",
            {"candidate": None},
            scope="PROOF_ONLY",
            checks={"signature": "PASS", "candidate_match": "NOT_RUN"},
        )
        mismatch_reason = "AMOUNT_MISMATCH" if kind == "payment_request" else "FIELD_MISMATCH"
        add(
            "single_field_changed",
            {"candidate_patch": {changed_field: changed_value}},
            status="TAMPERED",
            reasons=[mismatch_reason],
            checks={"signature": "PASS", "candidate_match": "FAIL"},
        )
        for field in fields:
            for label, changes in (
                ("missing", {"omit_candidate": [field]}),
                ("null", {"candidate_patch": {field: None}}),
            ):
                add(
                    f"{label}_{field}",
                    changes,
                    status="INCONCLUSIVE",
                    scope="PARTIAL_COMPARISON",
                    reasons=["INPUT_INCOMPLETE"],
                    checks={"signature": "PASS", "candidate_match": "NOT_RUN"},
                )
        add(
            "all_null",
            {"candidate_patch": dict.fromkeys(fields)},
            status="INCONCLUSIVE",
            scope="PARTIAL_COMPARISON",
            reasons=["INPUT_INCOMPLETE"],
        )
        add(
            "mismatch_over_missing",
            {"candidate_patch": {changed_field: changed_value}, "omit_candidate": [fields[-1]]},
            status="TAMPERED",
            scope="PARTIAL_COMPARISON",
            reasons=[mismatch_reason],
            checks={"signature": "PASS", "candidate_match": "FAIL"},
        )
        add(
            "wrong_network",
            {"chain_id": 31338},
            status="INCONCLUSIVE",
            scope="PROOF_ONLY",
            reasons=["NETWORK_MISMATCH"],
            checks={"contract": "FAIL", "signature": "NOT_RUN"},
        )
        for label, patch in (
            ("wrong_domain", {"app_domain": "originproof.mvp"}),
            ("wrong_version", {"schema_version": "1.0.0"}),
            ("invalid_period", {"expires_at": envelope["issued_at"]}),
            ("wrong_single_use", {"single_use": not envelope["single_use"]}),
            (
                "wrong_type",
                {
                    "proof_type": "OFFICIAL_DOCUMENT"
                    if kind == "payment_request"
                    else "PAYMENT_REQUEST"
                },
            ),
            ("untrusted_role", {"role": "operator"}),
        ):
            add(label, {"envelope_patch": patch}, layer="input_model")
        for label, delta in (("expiry_before", -1), ("expiry_at", 0), ("expiry_after", 1)):
            clock = datetime.fromisoformat(envelope["expires_at"]) + timedelta(seconds=delta)
            add(
                label,
                {"now": clock.isoformat()},
                reasons=[] if delta < 0 else ["PROOF_EXPIRED"],
                checks={"signature": "PASS", "candidate_match": "PASS"},
            )
        add(
            "missing_issuer",
            {"issuer": None},
            status="NOT_REGISTERED",
            scope="PROOF_ONLY",
            reasons=["ISSUER_NOT_FOUND"],
            checks={"issuer": "FAIL", "signature": "NOT_RUN"},
        )
        add(
            "missing_key",
            {"key": None},
            status="INCONCLUSIVE",
            scope="PROOF_ONLY",
            reasons=["KEY_NOT_FOUND"],
            checks={"issuer_key": "FAIL", "signature": "NOT_RUN"},
        )
        add(
            "other_issuer_key",
            {"key_patch": {"issuer_id": "iss_other_synthetic"}},
            status="INCONCLUSIVE",
            scope="PROOF_ONLY",
            reasons=["KEY_NOT_FOUND"],
            checks={"issuer_key": "FAIL", "signature": "NOT_RUN"},
        )
        for label, patch in (
            ("key_ends_at_issuance", {"valid_until": envelope["issued_at"]}),
            (
                "key_starts_after_issuance",
                {
                    "valid_from": (
                        datetime.fromisoformat(envelope["issued_at"]) + timedelta(seconds=1)
                    ).isoformat()
                },
            ),
        ):
            add(
                label,
                {"key_patch": patch},
                status="INCONCLUSIVE",
                scope="PROOF_ONLY",
                reasons=["KEY_TIME_INVALID"],
                checks={"issuer_key": "FAIL", "signature": "NOT_RUN"},
            )
        add(
            "key_expires_after_issuance",
            {
                "key_patch": {
                    "valid_until": (
                        datetime.fromisoformat(envelope["issued_at"]) + timedelta(seconds=1)
                    ).isoformat()
                }
            },
            checks={"signature": "PASS", "candidate_match": "PASS"},
        )
        add(
            "wrong_signer",
            {"key_patch": {"signer": "0x" + "bb" * 20}},
            status="TAMPERED",
            scope="PROOF_ONLY",
            reasons=["INVALID_SIGNATURE"],
            checks={"signature": "FAIL"},
        )
        add(
            "invalid_signature",
            {"envelope_patch": {"signature": "0x" + "00" * 65}},
            status="TAMPERED",
            scope="PROOF_ONLY",
            reasons=["INVALID_SIGNATURE"],
            checks={"signature": "FAIL", "candidate_match": "NOT_RUN"},
        )
        add(
            "payload_changed",
            {"payload_patch": {changed_field: changed_value}},
            status="TAMPERED",
            scope="PROOF_ONLY",
            reasons=["PAYLOAD_HASH_MISMATCH"],
            checks={"payload_hash": "FAIL", "signature": "NOT_RUN"},
        )
        add(
            "payload_and_hash_changed",
            {"payload_patch": {changed_field: changed_value}, "rehash_payload": True},
            status="TAMPERED",
            scope="PROOF_ONLY",
            reasons=["INVALID_SIGNATURE"],
            checks={"payload_hash": "PASS", "signature": "FAIL"},
        )
    return {
        "source": "synthetic",
        "fixture_version": "1.0.0",
        "schema_version": "2.0.0",
        "purpose": "W3-D1/D2 pure model/core cases; no live issuance or browser success",
        "basis_sha": "1f8ed632ea9c74091abaf2fe2ec32882038f731f",
        "profiles": profiles,
        "cases": cases,
    }


if __name__ == "__main__":
    Path(__file__).with_name("w3_cases.json").write_text(
        json.dumps(build_cases(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
