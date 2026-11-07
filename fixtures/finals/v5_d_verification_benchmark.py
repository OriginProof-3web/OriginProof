"""100 fresh verification requests; validate results before accepting a latency target."""

import argparse
import asyncio
import hashlib
import json
import math
import re
import subprocess
from collections import Counter
from pathlib import Path
from statistics import median
from time import perf_counter
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from originproof_core.wallet_contract import VerificationRequest, VerificationResult, WalletDomain

ROOT = Path(__file__).resolve().parents[2]
ATTEMPTS = 100


def validate_config(value: dict) -> dict:
    if (
        set(value) != {"source", "schema_version", "request", "expected"}
        or value["source"] != "synthetic"
        or value["schema_version"] != "v5-d-verification-benchmark-0.1"
    ):
        raise ValueError("synthetic benchmark configuration required")
    request = VerificationRequest.model_validate(value["request"], strict=True)
    expected = value["expected"]
    if (
        set(expected)
        != {
            "verification_status",
            "comparison_scope",
            "chain_id",
            "verifying_contract",
            "document_id",
            "version",
            "state",
            "warnings",
        }
        or expected["verification_status"] != "VERIFIED"
        or expected["comparison_scope"] != "FULL_COMPARISON"
        or expected["state"] != "ACTIVE"
        or expected["warnings"] != []
        or request.scope != "PROTECTED_FIELDS"
        or request.version is None
        or type(expected["version"]) is not int
        or (expected["document_id"], expected["version"]) != (request.document_id, request.version)
    ):
        raise ValueError("explicit normal full-comparison expectation required")
    WalletDomain(chainId=expected["chain_id"], verifyingContract=expected["verifying_contract"])
    return {**value, "request": request.model_dump(mode="json")}


def matches(result: VerificationResult, expected: dict) -> bool:
    document = result.document
    return bool(
        document is not None
        and {
            "verification_status": result.verification_status,
            "comparison_scope": result.comparison_scope,
            "chain_id": result.chain_id,
            "verifying_contract": result.verifying_contract,
            "document_id": document.document_id,
            "version": document.version,
            "state": document.state,
            "warnings": document.warnings,
        }
        == expected
    )


async def measure(
    client: httpx.AsyncClient, config: dict, *, scope: str, clock=perf_counter
) -> dict:
    config = validate_config(config)
    durations, errors, statuses = [], Counter(), Counter()
    correct = 0
    for _ in range(ATTEMPTS):
        started = clock()
        try:
            response = await client.post(
                "/v3/verifications",
                json=config["request"] | {"request_id": "req_d_perf_" + uuid4().hex},
            )
        except Exception:
            errors["TRANSPORT_OR_CLIENT_ERROR"] += 1
            durations.append(clock() - started)
            continue
        durations.append(clock() - started)
        statuses[str(response.status_code)] += 1
        if response.status_code != 200:
            errors["HTTP_STATUS"] += 1
            continue
        try:
            result = VerificationResult.model_validate_json(response.content, strict=True)
        except ValueError:
            errors["INVALID_RESPONSE"] += 1
            continue
        if matches(result, config["expected"]):
            correct += 1
        else:
            errors["UNEXPECTED_VERIFICATION_RESULT"] += 1
    if not all(math.isfinite(x) and x >= 0 for x in durations):
        raise ValueError("invalid monotonic timing")
    ordered = sorted(durations)
    p95 = ordered[math.ceil(0.95 * len(ordered)) - 1]
    return {
        "schema_version": "v5-d-verification-benchmark-result-0.1",
        "source": "synthetic",
        "scope": scope,
        "benchmark_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
        "attempts": ATTEMPTS,
        "matching_results": correct,
        "failures": ATTEMPTS - correct,
        "error_rate": (ATTEMPTS - correct) / ATTEMPTS,
        "http_status_counts": dict(statuses),
        "error_counts": dict(errors),
        "latency_seconds_all_attempts": {
            "p50": median(durations),
            "p95": p95,
            "max": max(durations),
        },
        "samples_seconds": durations,
        "functional_success": correct == ATTEMPTS,
        "p95_target_seconds": 3.0,
        "latency_target_met": p95 <= 3.0,
        "measurement_passed": correct == ATTEMPTS and p95 <= 3.0,
        "timing_boundary": "client POST roundtrip; client result validation excluded",
        "included": ["API processing", "DB session writes", "RPC reads if target uses them"],
        "not_invoked": ["AI", "chain writes"],
        "not_isolated": ["server core time", "RPC-only time", "internal cache effects"],
        "integration_acceptance": "NOT_DECLARED_BY_THIS_MEASUREMENT",
    }


def loopback_origin(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "::1"}
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.port is None
        or parsed.port == 0
    ):
        raise ValueError("explicit loopback HTTP origin and port required")
    return value.rstrip("/")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--api-origin", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[0-9a-f]{40}", args.candidate_sha):
            raise ValueError("full commit SHA required")
        origin = loopback_origin(args.api_origin)
        raw = args.config.read_bytes()
        if len(raw) > 65536:
            raise ValueError("configuration too large")
        config = validate_config(json.loads(raw))
        output = args.output or ROOT / "build/qa" / ("d-verification-perf-" + uuid4().hex + ".json")
        if output.exists():
            raise ValueError("output exists")
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
        plan = {
            "api_origin": origin,
            "candidate_sha_declared": args.candidate_sha,
            "qa_sha": sha,
            "server_sha_verified": False,
            "scope": "LOOPBACK_HTTP_UNATTESTED_TARGET",
            "requests": ATTEMPTS,
            "executed": False,
        }
        if not args.execute:
            print(json.dumps(plan))
            return 0

        async def run():
            async with httpx.AsyncClient(
                base_url=origin, timeout=10, trust_env=False, follow_redirects=False
            ) as client:
                return await measure(client, config, scope=plan["scope"])

        result = asyncio.run(run()) | plan | {"executed": True}
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with output.open("x") as stream:
            output.chmod(0o600)
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(
            json.dumps(
                {
                    "output": str(output),
                    "measurement_passed": result["measurement_passed"],
                    "matching_results": result["matching_results"],
                }
            )
        )
        return 0 if result["measurement_passed"] else 1
    except (ValueError, TypeError, KeyError, OSError, subprocess.CalledProcessError):
        print(json.dumps({"detail": "INVALID_BENCHMARK_CONFIGURATION_OR_OUTPUT"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
