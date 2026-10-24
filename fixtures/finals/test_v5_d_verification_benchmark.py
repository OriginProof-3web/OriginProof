"""Deterministic timing/failure checks and two-template ASGI synthetic measurements."""

import json
import os
import socket
from pathlib import Path

import httpx
import pytest
from originproof_core.wallet_contract import DocumentView, PublishMessage, VerificationResult
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_wallet_runtime import DOMAIN
from v5_d_verification_benchmark import loopback_origin, measure, validate_config
from v5_d_w3_content_qa import publication

pytest_plugins = ("test_wallet_runtime",)
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        socket.socket, "connect", lambda *a: pytest.fail("no live HTTP/RPC in unit QA")
    )


def configuration(content, doc):
    return {
        "source": "synthetic",
        "schema_version": "v5-d-verification-benchmark-0.1",
        "request": {
            "request_id": "req_d_perf_template",
            "document_id": doc.document_id,
            "version": doc.version,
            "scope": "PROTECTED_FIELDS",
            "candidate": content,
        },
        "expected": {
            "verification_status": "VERIFIED",
            "comparison_scope": "FULL_COMPARISON",
            "chain_id": DOMAIN.chain_id,
            "verifying_contract": DOMAIN.verifying_contract,
            "document_id": doc.document_id,
            "version": doc.version,
            "state": "ACTIVE",
            "warnings": [],
        },
    }


@pytest.fixture
def normal():
    golden = json.loads((ROOT / "fixtures/golden/wallet_contract_v1.json").read_text())
    vector = next(v for v in golden["vectors"] if v["label"] == "PAYMENT_REQUEST")
    message = PublishMessage.model_validate(vector["typed_data"]["message"])
    data = {
        name: getattr(message, name) for name in DocumentView.model_fields if hasattr(message, name)
    }
    doc = DocumentView(
        **data,
        latest_version=message.version,
        state="ACTIVE",
        warnings=[],
        original_available=False,
    )
    result = VerificationResult(
        session_id="vsn_synthetic_benchmark",
        verification_status="VERIFIED",
        comparison_scope="FULL_COMPARISON",
        document=doc,
        checks=[
            {"name": name, "status": "PASSED"} for name in ("signature", "content", "current_state")
        ],
        reason_codes=[],
        checked_at=message.issued_at + 1,
        chain_id=DOMAIN.chain_id,
        verifying_contract=DOMAIN.verifying_contract,
        block_number="10",
        block_hash="0x" + "ab" * 32,
    )
    return configuration(vector["protected_content"], doc), result.model_dump(mode="json")


@pytest.mark.parametrize(
    "fault", [None, "http", "schema", "transport", "inconclusive", "wrong_doc", "revoked"]
)
async def test_all_attempts_remain_in_latency_and_error_denominators(normal, fault):
    config, payload = normal
    calls = []

    def response(request):
        calls.append(json.loads(request.content))
        assert request.url.path == "/v3/verifications"
        if len(calls) == 1 or fault is None:
            return httpx.Response(200, json=payload)
        if fault == "transport":
            raise httpx.ConnectError("PRIVATE_TRANSPORT_PAYLOAD", request=request)
        if fault == "http":
            return httpx.Response(503, text="PRIVATE_RESPONSE_PAYLOAD")
        if fault == "schema":
            return httpx.Response(200, json={"PRIVATE_RESPONSE_PAYLOAD": True})
        changed = json.loads(json.dumps(payload))
        if fault == "inconclusive":
            changed["verification_status"] = "INCONCLUSIVE"
        elif fault == "wrong_doc":
            changed["document"]["document_id"] = "0x" + "ed" * 32
        else:
            changed["document"]["state"] = "REVOKED"
        return httpx.Response(200, json=changed)

    ticks = iter(t for i in range(100) for t in (float(i), i + (i + 1) / 1000))
    async with httpx.AsyncClient(
        base_url="http://test", transport=httpx.MockTransport(response)
    ) as client:
        result = await measure(
            client, config, scope="MOCK_TRANSPORT_TIMING_TEST", clock=lambda: next(ticks)
        )
    assert len(calls) == result["attempts"] == len(result["samples_seconds"]) == 100
    assert len({r["request_id"] for r in calls}) == 100
    assert result["matching_results"] == (100 if fault is None else 1)
    assert result["failures"] == (0 if fault is None else 99)
    assert result["error_rate"] == (0 if fault is None else 0.99)
    assert result["measurement_passed"] == (fault is None)
    assert result["latency_seconds_all_attempts"]["p50"] == pytest.approx(0.0505)
    assert result["latency_seconds_all_attempts"]["p95"] == pytest.approx(0.095)
    assert "PRIVATE_" not in json.dumps(result)


@pytest.mark.parametrize(
    "origin",
    [
        "https://example.invalid",
        "http://localhost:8000",
        "http://127.0.0.1:8000/api",
        "http://u:p@127.0.0.1:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000?x=1",
    ],
)
def test_cli_target_rejects_remote_credentials_and_paths(origin):
    with pytest.raises(ValueError):
        loopback_origin(origin)


def test_configuration_cannot_relabel_inconclusive_as_normal_success(normal):
    config, _ = normal
    config["expected"]["verification_status"] = "INCONCLUSIVE"
    with pytest.raises(ValueError):
        validate_config(config)
    assert loopback_origin("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"


@pytest.mark.parametrize("template", ["payment", "official"])
async def test_100_correct_verifications_against_same_head_asgi(wallet, template, tmp_path):
    from originproof_api.wallet_database import WalletVerificationRow

    signing, doc = await publication(wallet, template)
    result = await measure(
        wallet.client,
        configuration(signing["content"], doc),
        scope="ASGI_SQLITE_SYNTHETIC_REGISTRY",
    )
    assert result["functional_success"] and result["matching_results"] == 100
    assert wallet.chain.sends == []
    with Session(wallet.engine) as db:
        assert db.scalar(select(func.count()).select_from(WalletVerificationRow)) == 100
    out = Path(os.environ.get("D_PERF_REPORT_DIR", str(tmp_path)))
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{template}.json").write_text(json.dumps(result, indent=2) + "\n")
