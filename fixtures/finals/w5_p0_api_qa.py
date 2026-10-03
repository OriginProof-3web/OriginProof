"""D W5 candidate QA: owned socket HTTP/PostgreSQL/Anvil, no UI acceptance claim."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import io
import json
import os
import secrets
import socket
import subprocess
import sys
import tarfile
import threading
import time
import traceback
from contextlib import AsyncExitStack, contextmanager
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCT_SHA = "9651062c9f36e124b76796278c996764678e1c77"
W4_QA_SHA = "0bb5da42d64b9ce298cb2de2951b327da6bc4fc7"
W4_PREP_SHA = "78cce405357ae1f509a9bfebdbb07af4b02b2411"
DEPLOYER = "originproof-w5-d-qa-deployer:9651062"


def command(args, cwd=ROOT, timeout=240):
    result = subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"QA command failed: {args[0]} exit {result.returncode}")
    return result.stdout


def private_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        path.chmod(0o600)
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def materialize(out):
    """Read immutable Git objects; do not checkout or change another owner's branch."""
    product = out / "product"
    product.mkdir()
    with tarfile.open(fileobj=io.BytesIO(command(["git", "archive", PRODUCT_SHA]))) as archive:
        archive.extractall(product, filter="data")
    assert (product / "uv.lock").read_bytes() == (ROOT / "uv.lock").read_bytes()
    sources = {}
    for sha, path in (
        (W4_QA_SHA, "fixtures/finals/test_w4_lifecycle_qa.py"),
        (W4_QA_SHA, "fixtures/finals/w4_cases.json"),
        (W4_PREP_SHA, "fixtures/finals/prepare_w4_d3.py"),
    ):
        target = product / path
        assert not target.exists()
        blob = command(["git", "show", f"{sha}:{path}"])
        target.write_bytes(blob)
        sources[path] = {"sha": sha, "sha256": hashlib.sha256(blob).hexdigest()}
    (product / ".env").write_text("LLM_PROVIDER=mock\nOPENAI_MODEL=gpt-6-luna\n")
    (product / ".env").chmod(0o600)
    paths = [
        product / p
        for p in (
            "apps/api/src",
            "packages/python",
            "services/analyzer/src",
            "services/indexer/src",
        )
    ]
    sys.path[:0] = list(map(str, paths))
    os.environ["PYTHONPATH"] = ":".join(map(str, paths))
    command(
        [
            "docker",
            "build",
            "--label",
            f"org.opencontainers.image.revision={PRODUCT_SHA}",
            "-t",
            DEPLOYER,
            "-f",
            "infra/docker/deployer.Dockerfile",
            ".",
        ],
        cwd=product,
        timeout=600,
    )
    helper = load("w5_existing_w4_qa", product / "fixtures/finals/test_w4_lifecycle_qa.py")
    helper.PRODUCT_SHA, helper.DEPLOYER = PRODUCT_SHA, DEPLOYER
    prep = load("w5_existing_w4_prepare", product / "fixtures/finals/prepare_w4_d3.py")
    return product, helper, prep, sources


@contextmanager
def server(settings):
    import uvicorn
    from originproof_api.main import create_app

    app = create_app(settings=settings)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        api = uvicorn.Server(
            uvicorn.Config(
                app,
                log_level="critical",
                access_log=False,
                proxy_headers=False,
            )
        )
        thread = threading.Thread(target=api.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if api.started:
                    break
                if not thread.is_alive():
                    raise RuntimeError("owned API startup failed")
                time.sleep(0.1)
            else:
                raise RuntimeError("owned API startup timed out")
            yield url, app
        finally:
            api.should_exit = True
            thread.join(timeout=15)
            if thread.is_alive():
                raise RuntimeError("owned API thread did not close")


@contextmanager
def fresh_lifecycle_stack(helper, out, mixed_environment):
    """Preserve the original fixture's fresh DB/chain scope for its ordered clock tests."""
    if os.getenv("W5_D_MIXED_STACK_QA") == "1":
        # Diagnostic opt-in: reuse prior RPC/reorg state to reproduce the observed failure.
        yield mixed_environment
        return
    directory = out / "lifecycle"
    directory.mkdir(mode=0o700)
    resources = helper.disposable_stack.__wrapped__(directory)
    environment = None
    try:
        environment = next(resources)
        yield environment
    finally:
        resources.close()
        if environment is not None:
            prefix = environment["anvil"].removesuffix("-anvil")
            names = (
                command(
                    ["docker", "ps", "-a", "--filter", f"name={prefix}", "--format", "{{.Names}}"]
                )
                .decode()
                .splitlines()
            )
            networks = (
                command(
                    [
                        "docker",
                        "network",
                        "ls",
                        "--filter",
                        f"name={prefix}",
                        "--format",
                        "{{.Name}}",
                    ]
                )
                .decode()
                .splitlines()
            )
            assert not ({prefix + "-pg", prefix + "-anvil"} & set(names))
            assert prefix not in networks


async def run_checks(settings, url, app, prepared, helper, out, env_stack):
    from originproof_api.chain_management import ChainManagement
    from originproof_api.database import (
        AuditEventRow,
        Database,
        FinalsProofRow,
        IssuerKeyRow,
        OperationRow,
        RecipientTokenRow,
    )
    from sqlalchemy import func, select

    results = []
    database = Database(settings.database_url)

    async def counts():
        async with database.session_factory() as db:
            rows = {
                table.__name__: await db.scalar(select(func.count()).select_from(table))
                for table in (
                    FinalsProofRow,
                    IssuerKeyRow,
                    OperationRow,
                    AuditEventRow,
                    RecipientTokenRow,
                )
            }
        logs = await helper.rpc(
            settings.blockchain_rpc_url, "eth_getLogs", [{"fromBlock": "0x0", "toBlock": "latest"}]
        )
        return rows | {"chain_events": len(logs)}

    def expect(response, status):
        assert response.status_code == status, f"unexpected HTTP status {response.status_code}"
        return response.json()

    async def verdict(client, proof, status="VERIFIED", lifecycle="ACTIVE", candidate=None):
        body = {"request_id": f"req_w5_{uuid4().hex}"}
        if candidate is not None:
            body["candidate"] = candidate
        data = expect(await client.post(f"/v2/proofs/{proof}/verify", json=body), 200)
        assert (data["verification_status"], data["lifecycle_status"]) == (status, lifecycle)
        return data

    async def case(identifier, f_ids, action):
        try:
            evidence = await action()
            results.append(
                {"id": identifier, "f_ids": f_ids, "status": "PASS", "evidence": evidence}
            )
        except Exception as error:
            results.append(
                {
                    "id": identifier,
                    "f_ids": f_ids,
                    "status": "FAIL",
                    "error_type": type(error).__name__,
                    "failure_line": traceback.extract_tb(error.__traceback__)[-1].lineno,
                    "failure_trace": [
                        {"file": Path(frame.filename).name, "line": frame.lineno}
                        for frame in traceback.extract_tb(error.__traceback__)
                    ],
                }
            )

    try:
        async with AsyncExitStack() as stack:
            clients = {}
            for role, account in prepared["accounts"].items():
                client = await stack.enter_async_context(
                    httpx.AsyncClient(
                        base_url=url,
                        timeout=30,
                        trust_env=False,
                    )
                )
                login = expect(
                    await client.post(
                        "/v1/auth/login", json={k: account[k] for k in ("username", "password")}
                    ),
                    200,
                )
                client.headers["X-CSRF-Token"] = login["csrf_token"]
                clients[role] = client
            public = await stack.enter_async_context(
                httpx.AsyncClient(base_url=url, trust_env=False)
            )
            bank, office, recipient = (clients[k] for k in ("bank", "office", "recipient"))
            operator = clients["operator"]

            def profile(role):
                data = prepared["issuers"][role]
                candidate = {
                    k: v for k, v in data["new_issue_input"]["content"].items() if k != "proof_type"
                }
                return data["historical_proof_id"], candidate

            async def full_comparison():
                before = await counts()
                states = []
                for role in ("bank", "office"):
                    proof, candidate = profile(role)
                    result = await verdict(recipient, proof, candidate=candidate)
                    assert result["scope"] == "FULL_COMPARISON"
                    changed = candidate | (
                        {"amount_minor": candidate["amount_minor"] + 1}
                        if role == "bank"
                        else {"document_number": "SYNTHETIC-W5-CHANGED"}
                    )
                    mismatch = await verdict(recipient, proof, "TAMPERED", candidate=changed)
                    assert ("AMOUNT_MISMATCH" if role == "bank" else "FIELD_MISMATCH") in mismatch[
                        "reason_codes"
                    ]
                    states.append(
                        {
                            "type": role,
                            "scope": result["scope"],
                            "normal": "VERIFIED/ACTIVE",
                            "changed": "TAMPERED",
                        }
                    )
                assert await counts() == before
                return {
                    "states": states,
                    "reads_unchanged": True,
                    "issuance_layer": "API seed, not browser",
                }

            await case("two_types_comparison", ["F01", "F02"], full_comparison)

            async def mutation_permissions():
                proof, _ = profile("bank")
                application = expect(await bank.get("/v1/issuer-applications/mine"), 200)
                operations = expect(await bank.get("/v1/operations"), 200)
                key = prepared["issuers"]["bank"]["old_key_id"]
                mutate = {"request_id": f"req_w5_denied_{uuid4().hex}", "reason": "synthetic"}
                proof_body = {"request_id": f"req_w5_denied_{uuid4().hex}"}
                matrix = [
                    (
                        f"/v1/operator/issuer-applications/{application['application_id']}/decision",
                        {"decision": "APPROVE", "reason": "synthetic"},
                        operator,
                        recipient,
                    ),
                    (
                        f"/v1/operator/issuer-applications/{application['application_id']}/activate",
                        mutate,
                        operator,
                        recipient,
                    ),
                    (
                        f"/v1/operator/issuers/{settings.finals_payment_issuer_id}/suspend",
                        mutate,
                        operator,
                        recipient,
                    ),
                    (
                        "/v1/issuer/keys",
                        prepared["issuers"]["bank"]["rotation_input"],
                        bank,
                        recipient,
                    ),
                    (
                        "/v1/issuer/keys/rotate",
                        prepared["issuers"]["bank"]["rotation_input"],
                        bank,
                        recipient,
                    ),
                    (f"/v1/issuer/keys/{key}/revoke", mutate, bank, recipient),
                    (
                        "/v2/issuer/proofs",
                        prepared["issuers"]["bank"]["new_issue_input"],
                        bank,
                        recipient,
                    ),
                    (f"/v2/issuer/proofs/{proof}/register", proof_body, bank, recipient),
                    (f"/v2/issuer/proofs/{proof}/revoke", mutate, bank, recipient),
                    (f"/v2/proofs/{proof}/consume", proof_body, recipient, operator),
                ]
                before = await counts()
                for path, body, authorized, unauthorized in matrix:
                    expect(await public.post(path, json=body), 401)
                    expect(
                        await unauthorized.post(path, json=body),
                        404 if path.endswith("/consume") else 403,
                    )
                    token = authorized.headers.pop("X-CSRF-Token")
                    try:
                        expect(await authorized.post(path, json=body), 403)
                    finally:
                        authorized.headers["X-CSRF-Token"] = token
                    expect(
                        await authorized.post(
                            path,
                            json=body
                            | {
                                "actor_id": "acct_synthetic_injected",
                                "issuer_id": "iss_synthetic_injected",
                            },
                        ),
                        422,
                    )
                recover = f"/v1/operations/{operations[0]['operation_id']}/recover"
                expect(await public.post(recover), 401)
                token = bank.headers.pop("X-CSRF-Token")
                try:
                    expect(await bank.post(recover), 403)
                finally:
                    bank.headers["X-CSRF-Token"] = token
                expect(await office.post(recover), 404)
                altered = prepared["issuers"]["bank"]["new_issue_input"]
                # The seed request exists. Changing only its amount must conflict, not reissue.
                altered = altered | {
                    "request_id": "req_d3_seed_proof_bank",
                    "content": altered["content"] | {"amount_minor": 10001},
                }
                expect(await bank.post("/v2/issuer/proofs", json=altered), 409)
                assert await counts() == before
                return {
                    "mutation_paths": len(matrix),
                    "anonymous": 401,
                    "management_wrong_role": 403,
                    "consume_nonowner": 404,
                    "missing_csrf": 403,
                    "actor_injection": 422,
                    "operation_recovery_nonowner": 404,
                    "changed_same_request": 409,
                    "db_and_chain_unchanged": True,
                }

            await case(
                "mutation_permission_matrix", ["F05", "F10", "F12", "F15"], mutation_permissions
            )

            async def missing():
                before = await counts()
                proof = f"prf_w5_unknown_{uuid4().hex}"
                assert (
                    expect(await public.get(f"/v2/proofs/{proof}"), 404)["detail"]
                    == "PROOF_NOT_FOUND"
                )
                result = await verdict(public, proof, "NOT_REGISTERED", None)
                assert result["reason_codes"] == ["PROOF_NOT_FOUND"]
                assert set(result["checks"].values()) == {"NOT_RUN"}
                manager = ChainManagement(database, settings)
                assert await manager.reader("iss_w5_unknown").get_issuer("iss_w5_unknown") is None
                assert await counts() == before
                return {
                    "get": 404,
                    "verify": "NOT_REGISTERED/null",
                    "issuer_reader": None,
                    "counts_unchanged": True,
                }

            await case("unregistered", ["F06"], missing)

            async def permissions():
                before = await counts()
                proof, candidate = profile("bank")
                assert (await public.get(f"/v2/proofs/{proof}/content")).status_code == 401
                for role in ("office", "other_recipient", "operator"):
                    assert (
                        await clients[role].get(f"/v2/proofs/{proof}/content")
                    ).status_code == 404
                    assert (
                        await clients[role].post(
                            f"/v2/proofs/{proof}/verify",
                            json={
                                "request_id": f"req_w5_{uuid4().hex}",
                                "candidate": candidate,
                            },
                        )
                    ).status_code == 404
                assert (
                    await office.get(f"/v1/issuer/keys/{prepared['issuers']['bank']['old_key_id']}")
                ).status_code == 404
                assert (
                    await office.post(
                        f"/v2/issuer/proofs/{proof}/revoke",
                        json={
                            "request_id": f"req_w5_{uuid4().hex}",
                            "reason": "synthetic",
                        },
                    )
                ).status_code == 404
                assert await counts() == before
                return {"anonymous": 401, "nonowners": 404, "denied_mutation_unchanged": True}

            await case("ownership", ["F05", "F10", "F14", "F15"], permissions)

            async def status_scopes():
                before = await counts()
                proof, _ = profile("bank")
                own = expect(await bank.get("/v1/operations", params={"target_id": proof}), 200)
                assert len(own) == 1 and own[0]["status"] == "CONFIRMED"
                assert own[0]["next_action"] == "NONE" and not own[0]["recovery_required"]
                assert not ({"input_body", "recovery_reference"} & own[0].keys())
                assert (
                    expect(await office.get("/v1/operations", params={"target_id": proof}), 200)
                    == []
                )
                assert (
                    await office.get(f"/v1/operations/{own[0]['operation_id']}")
                ).status_code == 404
                audits = expect(
                    await bank.get("/v1/audit-events", params={"target_id": proof}), 200
                )
                assert audits and all(
                    x["issuer_id"] == prepared["accounts"]["bank"]["issuer_id"] for x in audits
                )
                assert (
                    expect(await office.get("/v1/audit-events", params={"target_id": proof}), 200)
                    == []
                )
                assert (await recipient.get("/v1/audit-events")).status_code == 403
                assert (await bank.get("/v1/operations?limit=201")).status_code == 422
                assert (await bank.get("/v1/audit-events?offset=-1")).status_code == 422
                path = f"/v2/issuer/proofs/{proof}/reconciliation"
                reconciliation = expect(await bank.get(path), 200)
                assert reconciliation["authority"] == "CANONICAL_READER"
                assert reconciliation["registration_consistent"] is True
                assert (await operator.get(path)).status_code == 200
                assert (await office.get(path)).status_code == 404
                assert (await recipient.get(path)).status_code == 403
                sync = expect(await operator.get("/v1/chain-sync"), 200)
                assert sync["authority"] == "HISTORICAL_EVENTS_ONLY"
                assert (await recipient.get("/v1/chain-sync")).status_code == 403
                assert await counts() == before
                return {
                    "confirmed_guidance": "NONE",
                    "institution_isolated": True,
                    "reconciliation": True,
                    "projection_authority": sync["authority"],
                    "reads_unchanged": True,
                }

            await case("operation_audit_reconciliation", ["F05", "F13", "F15"], status_scopes)

            async def suspension():
                observations = []
                for role in ("bank", "office"):
                    issuer_id = prepared["accounts"][role]["issuer_id"]
                    path = f"/v1/operator/issuers/{issuer_id}"
                    body = {"request_id": f"req_w5_{uuid4().hex}", "reason": "Synthetic W5 QA"}
                    assert (
                        expect(await operator.post(path + "/suspend", json=body), 200)["status"]
                        == "CONFIRMED"
                    )
                    try:
                        before = await counts()
                        issue = prepared["issuers"][role]["new_issue_input"] | {
                            "request_id": f"req_w5_{uuid4().hex}"
                        }
                        denied = expect(
                            await clients[role].post("/v2/issuer/proofs", json=issue), 409
                        )
                        assert denied["detail"] == "ISSUER_NOT_ACTIVE"
                        proof, candidate = profile(role)
                        state = await verdict(
                            recipient, proof, lifecycle="ISSUER_SUSPENDED", candidate=candidate
                        )
                        assert "ISSUER_SUSPENDED" in state["reason_codes"]
                        assert await counts() == before
                    finally:
                        restored = await operator.post(
                            path + "/reactivate",
                            json=body | {"request_id": f"req_w5_{uuid4().hex}"},
                        )
                        assert expect(restored, 200)["status"] == "CONFIRMED"
                    await verdict(recipient, proof, candidate=candidate)
                    observations.append(
                        {
                            "type": role,
                            "new_issue": "409 ISSUER_NOT_ACTIVE",
                            "existing": "VERIFIED/ISSUER_SUSPENDED",
                            "restored": "ACTIVE",
                            "denial_unchanged": True,
                        }
                    )
                return {"institutions": observations}

            await case("suspended_new_issuance", ["F11"], suspension)

            async def rpc_outage():
                before = await counts()
                proof, _ = profile("bank")
                command(["docker", "stop", env_stack["anvil"]])
                try:
                    result = await verdict(public, proof, "INCONCLUSIVE", None)
                    assert "DEPENDENCY_UNAVAILABLE" in result["reason_codes"]
                    row = expect(await bank.get(f"/v2/issuer/proofs/{proof}/reconciliation"), 200)
                    assert row["registration_consistent"] is None
                finally:
                    command(["docker", "start", env_stack["anvil"]])
                for _ in range(60):
                    try:
                        await helper.rpc(settings.blockchain_rpc_url, "eth_chainId", [])
                        break
                    except httpx.HTTPError:
                        await asyncio.sleep(0.1)
                await verdict(public, proof)
                assert await counts() == before
                return {
                    "down": "INCONCLUSIVE/null",
                    "reconciliation": None,
                    "recovered": "VERIFIED/ACTIVE",
                    "counts_unchanged": True,
                }

            await case("rpc_outage_recovery", ["F13"], rpc_outage)

            async def boundary_loss():
                from infrastructure.blockchain.writer import ChainOperationState

                writer = app.state.chain_management.writer
                original = writer.submit_prepared
                sends = 0

                async def lose_hash(transaction):
                    nonlocal sends
                    sends += 1
                    result = await original(transaction)
                    assert result.state == ChainOperationState.SUBMITTED
                    return replace(
                        result,
                        state=ChainOperationState.UNKNOWN,
                        tx_hash=None,
                        error_code="SUBMISSION_UNKNOWN",
                    )

                writer.submit_prepared = lose_hash
                try:
                    body = prepared["issuers"]["bank"]["rotation_input"] | {
                        "request_id": f"req_w5_{uuid4().hex}"
                    }
                    pending = expect(await bank.post("/v1/issuer/keys", json=body), 200)
                    assert pending["status"] == "UNKNOWN"
                    row = expect(await bank.get(f"/v1/operations/{pending['operation_id']}"), 200)
                    assert (
                        row["recovery_required"] and row["next_action"] == "RECOVER_SAME_OPERATION"
                    )
                    recovered = expect(
                        await bank.post(f"/v1/operations/{pending['operation_id']}/recover"), 200
                    )
                    assert recovered["status"] == "CONFIRMED" and recovered["next_action"] == "NONE"
                    repeated = expect(await bank.post("/v1/issuer/keys", json=body), 200)
                    assert (
                        repeated["operation_id"] == recovered["operation_id"]
                        and repeated["tx_hash"] == recovered["tx_hash"]
                    )
                    assert sends == 1
                    return {
                        "before": "UNKNOWN/RECOVER_SAME_OPERATION",
                        "after": "CONFIRMED/NONE",
                        "same_operation_and_tx": True,
                        "actual_submissions": sends,
                        "injection": (
                            "in-process returned hash loss after actual Anvil submit; "
                            "not socket response loss or process restart"
                        ),
                    }
                finally:
                    writer.submit_prepared = original

            await case("same_operation_recovery", ["F12", "F13"], boundary_loss)

            async def privacy():
                before = await counts()
                public_responses = []
                for role in ("bank", "office"):
                    proof, _ = profile(role)
                    view = expect(await public.get(f"/v2/proofs/{proof}"), 200)
                    assert not (
                        {
                            "envelope",
                            "payload",
                            "recipient_id",
                            "subject_binding_hash",
                            "recipient_salt",
                            "token",
                            "secret_ref",
                            "private_key",
                        }
                        & view.keys()
                    )
                    keys = expect(await clients[role].get("/v1/issuer/keys"), 200)
                    public_responses.append(json.dumps(view).encode())
                    public_responses.append(json.dumps(keys).encode())
                    assert all(
                        not ({"secret_ref", "private_key", "password", "token"} & x.keys())
                        for x in keys
                    )
                assert await counts() == before
                directory = Path(settings.signer_directory)
                assert directory.stat().st_mode & 0o777 == 0o700
                files = list(directory.glob("key_*"))
                assert files and all(
                    not p.is_symlink()
                    and p.stat().st_mode & 0o777 == 0o600
                    and p.stat().st_size == 32
                    and p.stat().st_uid == os.getuid()
                    for p in files
                )
                sensitive = [x["password"].encode() for x in prepared["accounts"].values()]
                sensitive += [p.read_bytes() for p in files]
                async with database.session_factory() as db:
                    tokens = list(await db.scalars(select(RecipientTokenRow.token)))
                sensitive += [bytes.fromhex(token) for token in tokens]
                # Check both UTF-8 and raw/hex encodings of this run's known synthetic secrets.
                patterns = sensitive + [value.hex().encode() for value in sensitive]
                tip = int(await helper.rpc(settings.blockchain_rpc_url, "eth_blockNumber", []), 16)
                chain_bytes = []
                transaction_count = 0
                for number in range(tip + 1):
                    block = await helper.rpc(
                        settings.blockchain_rpc_url, "eth_getBlockByNumber", [hex(number), True]
                    )
                    for transaction in block["transactions"]:
                        chain_bytes.append(bytes.fromhex(transaction["input"][2:]))
                        transaction_count += 1
                logs = await helper.rpc(
                    settings.blockchain_rpc_url,
                    "eth_getLogs",
                    [{"fromBlock": "0x0", "toBlock": "latest"}],
                )
                for item in logs:
                    chain_bytes.extend(
                        bytes.fromhex(value[2:]) for value in [item["data"], *item["topics"]]
                    )
                tracked = command(["git", "ls-files", "-z"]).decode().split("\0")
                tracked_bytes = [
                    (ROOT / path).read_bytes()
                    for path in tracked
                    if path and (ROOT / path).is_file()
                ]
                assert all(
                    pattern not in blob
                    for blob in [*public_responses, *chain_bytes, *tracked_bytes]
                    for pattern in patterns
                )
                assert await counts() == before
                return {
                    "public_proof_and_key_fields": "selected_forbidden_fields_absent",
                    "signer_files": "0600",
                    "signer_directory": "0700",
                    "read_only": True,
                    "known_synthetic_secret_scan": {
                        "public_responses": len(public_responses),
                        "chain_transactions": transaction_count,
                        "chain_logs": len(logs),
                        "tracked_files": len(tracked_bytes),
                        "leaks": 0,
                    },
                    "scope": (
                        "selected API responses, signer modes, owned chain input/log and tracked "
                        "files for this run's known secrets; no whole browser/log audit claim"
                    ),
                }

            await case("private_fields", ["F15"], privacy)
            baseline = await counts()
            private_json(out / "counts.json", baseline)
    finally:
        await database.dispose()
    return results


async def approval_boundaries(settings, prepared, helper):
    from originproof_api.accounts import password_hash
    from originproof_api.database import (
        AccountRow,
        AuditEventRow,
        Database,
        FinalsProofRow,
        IssuerKeyRow,
        OperationRow,
    )
    from sqlalchemy import func, select

    suffix = uuid4().hex[:10]
    issuer_ids = {role: f"iss_w5_{role}_{suffix}" for role in ("pending", "rejected")}
    accounts = {
        role: {
            "account_id": f"acct_w5_{role}_{suffix}",
            "username": f"w5_{role}_{suffix}",
            "issuer_id": issuer_ids[role],
            "password": secrets.token_urlsafe(24),
        }
        for role in issuer_ids
    }
    isolated = settings.model_copy(
        update={
            "finals_payment_issuer_id": issuer_ids["pending"],
            "finals_document_issuer_id": issuer_ids["rejected"],
        }
    )
    database = Database(settings.database_url)

    async def unchanged_counts():
        async with database.session_factory() as db:
            values = [
                await db.scalar(select(func.count()).select_from(table))
                for table in (FinalsProofRow, IssuerKeyRow, OperationRow, AuditEventRow)
            ]
        logs = await helper.rpc(
            settings.blockchain_rpc_url, "eth_getLogs", [{"fromBlock": "0x0", "toBlock": "latest"}]
        )
        return values + [len(logs)]

    try:
        async with database.session_factory() as db:
            db.add_all(
                [
                    AccountRow(
                        **{k: v for k, v in account.items() if k != "password"},
                        role="issuer",
                        password_hash=password_hash(account["password"]),
                    )
                    for account in accounts.values()
                ]
            )
            await db.commit()
        with server(isolated) as (url, _):
            async with AsyncExitStack() as stack:
                clients = {}
                for role, account in (
                    accounts | {"operator": prepared["accounts"]["operator"]}
                ).items():
                    client = await stack.enter_async_context(
                        httpx.AsyncClient(base_url=url, trust_env=False, timeout=30)
                    )
                    login = await client.post(
                        "/v1/auth/login", json={k: account[k] for k in ("username", "password")}
                    )
                    assert login.status_code == 200
                    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
                    clients[role] = client
                applications = {}
                for role in accounts:
                    response = await clients[role].post(
                        "/v1/issuer-applications", json={"issuer_name": f"Synthetic W5 {role}"}
                    )
                    assert response.status_code == 201
                    applications[role] = response.json()["application_id"]
                evidence = []
                for role, decision in (
                    ("pending", None),
                    ("pending", "APPROVE"),
                    ("rejected", "REJECT"),
                ):
                    if decision:
                        response = await clients["operator"].post(
                            f"/v1/operator/issuer-applications/{applications[role]}/decision",
                            json={"decision": decision, "reason": "synthetic W5 QA"},
                        )
                        assert response.status_code == 200
                    state = (await clients[role].get("/v1/issuer-applications/mine")).json()[
                        "status"
                    ]
                    before = await unchanged_counts()
                    response = await clients[role].post(
                        "/v1/issuer/keys",
                        json={
                            **prepared["issuers"]["bank"]["rotation_input"],
                            "request_id": f"req_w5_pending_{uuid4().hex}",
                        },
                    )
                    assert response.status_code == 409
                    assert response.json()["detail"] == "ISSUER_NOT_ACTIVE"
                    profile = "bank" if role == "pending" else "office"
                    response = await clients[role].post(
                        "/v2/issuer/proofs",
                        json={
                            **prepared["issuers"][profile]["new_issue_input"],
                            "request_id": f"req_w5_pending_{uuid4().hex}",
                        },
                    )
                    assert response.status_code == 409
                    assert response.json()["detail"] == "ISSUING_KEY_UNAVAILABLE"
                    assert await unchanged_counts() == before
                    evidence.append(
                        {
                            "application_status": state,
                            "key_http": 409,
                            "proof_http": 409,
                            "denial_unchanged": True,
                        }
                    )
                return {"states": evidence, "layer": "socket HTTP/actual PostgreSQL/Anvil"}
    finally:
        await database.dispose()


async def limits(url):
    async with httpx.AsyncClient(base_url=url, timeout=20, trust_env=False) as client:
        for number in range(120):
            response = await client.get(
                "/v1/auth/me", headers={"X-Forwarded-For": f"198.51.100.{number % 250 + 1}"}
            )
            assert response.status_code == 401
        response = await client.get(
            "/v2/proofs/prf_w5_missing", headers={"X-Forwarded-For": "203.0.113.99"}
        )
        assert response.status_code == 429 and response.json() == {"error": "RATE_LIMITED"}
        assert 1 <= int(response.headers["Retry-After"]) <= 60
        assert response.headers["Cache-Control"] == "no-store"
        assert (await client.get("/health/live")).status_code == 200
        return {
            "configured_default": 120,
            "first_120": 401,
            "next_request": 429,
            "xff_does_not_bypass": True,
            "health_live": 200,
        }


async def login_limits(url):
    async with httpx.AsyncClient(base_url=url, trust_env=False) as client:
        for _ in range(10):
            assert (
                await client.post(
                    "/v1/auth/login",
                    json={"username": "synthetic_missing", "password": "synthetic_wrong"},
                )
            ).status_code == 401
        response = await client.post(
            "/v1/auth/login", json={"username": "synthetic_missing", "password": "synthetic_wrong"}
        )
        assert response.status_code == 429 and response.json()["error"] == "RATE_LIMITED"
        return {"configured_default": 10, "first_10": 401, "next_login": 429}


async def security_boundaries(url):
    async with httpx.AsyncClient(base_url=url, timeout=20, trust_env=False) as client:
        body = {"username": "synthetic_missing", "password": "synthetic_wrong"}
        for headers in (
            {"Origin": "https://synthetic.invalid"},
            {"Sec-Fetch-Site": "cross-site"},
        ):
            response = await client.post("/v1/auth/login", json=body, headers=headers)
            assert response.status_code == 403
            assert response.json() == {"error": "ORIGIN_FORBIDDEN"}
        response = await client.post("/v1/auth/login", content=b"x" * 65537)
        assert response.status_code == 413
        assert response.json() == {"error": "REQUEST_TOO_LARGE"}

        async def large_chunks():
            yield b"x" * 40000
            yield b"x" * 30000

        response = await client.post("/v1/auth/login", content=large_chunks())
        assert response.status_code == 413
        assert response.json() == {"error": "REQUEST_TOO_LARGE"}

        async def slow_chunks():
            yield b"{"
            await asyncio.sleep(10.3)
            yield b"}"

        response = await client.post("/v1/auth/login", content=slow_chunks())
        assert response.status_code == 408
        assert response.json() == {"error": "REQUEST_TIMEOUT"}
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        return {
            "origin_and_cross_site": 403,
            "default_max_bytes": 65536,
            "declared_and_chunked_oversize": 413,
            "default_body_timeout_seconds": 10,
            "slow_body": 408,
        }


def other_network(settings, prepared, helper, chain_id):
    """Use a different real RPC, preserving the original manifest and signed records."""
    name = f"originproof-w5-d-other-chain-{uuid4().hex[:12]}"
    try:
        command(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "-p",
                "127.0.0.1::8545",
                "--entrypoint",
                "anvil",
                helper.FOUNDRY,
                "--host",
                "0.0.0.0",
                "--chain-id",
                str(chain_id),
            ]
        )
        port = command(["docker", "port", name, "8545/tcp"]).decode().strip().split(":")[-1]
        rpc_url = f"http://127.0.0.1:{port}"
        manifest = json.loads(Path(settings.blockchain_manifest_path).read_text())

        async def observe():
            for _ in range(60):
                try:
                    observed = await helper.rpc(rpc_url, "eth_chainId", [])
                    break
                except httpx.HTTPError:
                    await asyncio.sleep(0.1)
            else:
                raise RuntimeError("owned alternate Anvil startup failed")
            assert int(observed, 16) == chain_id
            for _ in range(manifest["deployment_block"] + 1):
                await helper.rpc(rpc_url, "evm_mine", [])
            block = await helper.rpc(
                rpc_url, "eth_getBlockByNumber", [hex(manifest["deployment_block"]), False]
            )
            assert block["hash"] != manifest["deployment_block_hash"]
            return {
                "observed_rpc_chain_id": chain_id,
                "deployment_block_hash_matches": False,
                "alternate_environment": "fresh empty Anvil; no Contract redeployment",
            }

        observation = asyncio.run(observe())
        # Only the RPC changes: app/manifest/envelope still expect the original 31337.
        alternate = settings.model_copy(update={"blockchain_rpc_url": rpc_url})
        with server(alternate) as (url, _):

            async def rejected():
                async with httpx.AsyncClient(base_url=url, trust_env=False, timeout=30) as client:
                    proof = prepared["issuers"]["bank"]["historical_proof_id"]
                    response = await client.post(
                        f"/v2/proofs/{proof}/verify",
                        json={
                            "request_id": f"req_w5_{uuid4().hex}",
                        },
                    )
                    assert response.status_code == 200
                    verdict = response.json()
                    assert verdict["verification_status"] == "INCONCLUSIVE"
                    assert verdict["lifecycle_status"] is None
                    assert "DEPENDENCY_UNAVAILABLE" in verdict["reason_codes"]
                    return observation | {
                        "known_original_signed_proof": "INCONCLUSIVE/null/DEPENDENCY_UNAVAILABLE",
                        "scope": (
                            "real RPC identity/deployment guard; "
                            "not signature submission to another Contract"
                        ),
                    }

            result = asyncio.run(rejected())
    finally:
        existing = (
            command(["docker", "ps", "-a", "--filter", f"name={name}", "--format", "{{.Names}}"])
            .decode()
            .splitlines()
        )
        if name in existing:
            command(["docker", "rm", "-f", name])
        remaining = (
            command(["docker", "ps", "-a", "--filter", f"name={name}", "--format", "{{.Names}}"])
            .decode()
            .splitlines()
        )
        assert name not in remaining
    return result | {"owned_alternate_container_absent": True}


def main():
    if os.getenv("W5_D_API_QA") != "1":
        raise SystemExit("W5_D_API_QA=1 required for owned disposable provisioning")
    os.environ.update(LLM_PROVIDER="mock", OPENAI_MODEL="gpt-6-luna")
    os.environ.pop("OPENAI_API_KEY", None)
    out = ROOT / "build/w5-d-api" / uuid4().hex
    out.mkdir(parents=True, mode=0o700)
    summary = {
        "product_sha": PRODUCT_SHA,
        "qa_git_head": command(["git", "rev-parse", "HEAD"]).decode().strip(),
        "qa_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "projection_source_sha256": hashlib.sha256(
            (ROOT / "fixtures/finals/w5_projection_qa.py").read_bytes()
        ).hexdigest(),
        "qa_git_dirty": bool(command(["git", "status", "--porcelain"])),
        "browser_e2e": "NOT_RUN",
        "lifecycle_fixture_mode": (
            "MIXED_DIAGNOSTIC" if os.getenv("W5_D_MIXED_STACK_QA") == "1" else "FRESH"
        ),
        "results": [],
        "resources_closed": False,
    }
    resources = None
    env_stack = None
    try:
        product, helper, prep, sources = materialize(out)
        summary["reused_qa_sources"] = sources
        summary["environment"] = {
            "python": sys.version.split()[0],
            "required_python": "3.13.0",
            "llm_provider": "mock",
            "openai_model": "gpt-6-luna",
            "paid_calls": 0,
            "foundry_image": helper.FOUNDRY,
            "source_config_sha256": {
                path: hashlib.sha256((product / path).read_bytes()).hexdigest()
                for path in (
                    "uv.lock",
                    ".tool-versions",
                    "docker-compose.yml",
                    "infra/docker/api.Dockerfile",
                    "infra/docker/deployer.Dockerfile",
                )
            },
        }
        from originproof_api.settings import Settings

        resources = helper.disposable_stack.__wrapped__(out)
        env_stack = next(resources)
        settings = Settings(
            _env_file=None,
            database_url=env_stack["database_url"],
            blockchain_rpc_url=env_stack["rpc_url"],
            blockchain_manifest_path=env_stack["manifest"],
            signer_directory=str(out / "signers"),
            blockchain_chain_id=31337,
            finals_payment_issuer_id=f"iss_w5_bank_{uuid4().hex[:8]}",
            finals_document_issuer_id=f"iss_w5_office_{uuid4().hex[:8]}",
            requests_per_minute=1000,
            logins_per_minute=100,
        )
        summary["functional_budget_override"] = {
            "requests_per_minute": 1000,
            "logins_per_minute": 100,
        }
        with server(settings) as (url, app):
            prepared = asyncio.run(prep.seed(settings, url))
            summary["results"] = asyncio.run(
                run_checks(settings, url, app, prepared, helper, out, env_stack)
            )
        try:
            evidence = asyncio.run(approval_boundaries(settings, prepared, helper))
            summary["results"].append(
                {
                    "id": "approval_chain_boundary",
                    "f_ids": ["F09"],
                    "status": "PASS",
                    "evidence": evidence,
                }
            )
        except Exception as error:
            summary["results"].append(
                {
                    "id": "approval_chain_boundary",
                    "status": "FAIL",
                    "error_type": type(error).__name__,
                    "failure_line": traceback.extract_tb(error.__traceback__)[-1].lineno,
                }
            )
        for identifier, action in (
            ("default_request_limit", limits),
            ("default_login_limit", login_limits),
            ("origin_body_boundaries", security_boundaries),
        ):
            defaults = Settings(
                **(settings.model_dump() | {"requests_per_minute": 120, "logins_per_minute": 10}),
                _env_file=None,
            )
            try:
                with server(defaults) as (url, _):
                    evidence = asyncio.run(action(url))
                summary["results"].append(
                    {"id": identifier, "f_ids": ["F15"], "status": "PASS", "evidence": evidence}
                )
            except Exception as error:
                summary["results"].append(
                    {
                        "id": identifier,
                        "f_ids": ["F15"],
                        "status": "FAIL",
                        "error_type": type(error).__name__,
                    }
                )
        for identifier, chain_id in (
            ("different_rpc_chain", 31338),
            ("same_chain_fresh_rpc_guard", 31337),
        ):
            try:
                evidence = other_network(settings, prepared, helper, chain_id)
                summary["results"].append(
                    {
                        "id": identifier,
                        "f_ids": ["F14"],
                        "status": "PASS",
                        "evidence": evidence,
                    }
                )
            except Exception as error:
                summary["results"].append(
                    {
                        "id": identifier,
                        "f_ids": ["F14"],
                        "status": "FAIL",
                        "error_type": type(error).__name__,
                        "failure_line": traceback.extract_tb(error.__traceback__)[-1].lineno,
                    }
                )
        try:
            projection = load("w5_projection_qa", ROOT / "fixtures/finals/w5_projection_qa.py")
            evidence = projection.run(settings, prepared, helper, env_stack, out)
            summary["results"].append(
                {
                    "id": "projection_replay_process_restart_reorg",
                    "f_ids": ["F13"],
                    "status": "PASS",
                    "evidence": evidence,
                }
            )
        except Exception as error:
            summary["results"].append(
                {
                    "id": "projection_replay_process_restart_reorg",
                    "status": "FAIL",
                    "error_type": type(error).__name__,
                    "failure_line": traceback.extract_tb(error.__traceback__)[-1].lineno,
                }
            )
        lifecycle_errors = []
        try:
            for profile, policy_case in helper.POLICY_CASES:
                helper.test_w4_policy(profile, policy_case)
            original_post = httpx.AsyncClient.post

            async def observed_post(client, path, *args, **kwargs):
                response = await original_post(client, path, *args, **kwargs)
                if str(path) == "/v2/issuer/proofs" and response.status_code != 200:
                    code = response.json().get("detail", response.json().get("error"))
                    if not isinstance(code, str) or not all(
                        char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ_" for char in code
                    ):
                        code = "REDACTED"
                    lifecycle_errors.append({"http_status": response.status_code, "code": code})
                elif str(path).endswith("/verify") and response.status_code == 200:
                    view = response.json()
                    if view.get("verification_status") != "VERIFIED":
                        lifecycle_errors.append(
                            {
                                k: view[k]
                                for k in (
                                    "verification_status",
                                    "lifecycle_status",
                                    "reason_codes",
                                    "checks",
                                )
                            }
                        )
                return response

            with pytest.MonkeyPatch.context() as monkeypatch:
                monkeypatch.setattr(httpx.AsyncClient, "post", observed_post)
                # Old W4 functional fixture predates W5 limits; limits have separate default tests.
                monkeypatch.setattr(
                    helper,
                    "Settings",
                    lambda **kw: Settings(**kw, requests_per_minute=1000, logins_per_minute=100),
                )
                with fresh_lifecycle_stack(helper, out, env_stack) as lifecycle_environment:
                    asyncio.run(
                        helper.test_w4_real_database_and_chain(lifecycle_environment, monkeypatch)
                    )
            summary["results"].append(
                {
                    "id": "current_candidate_lifecycle_regression",
                    "f_ids": ["F01", "F03", "F04", "F05", "F07", "F08", "F10", "F14"],
                    "status": "PASS",
                    "evidence": {
                        "core_vector_function_calls": len(helper.POLICY_CASES),
                        "ordered_asgi_function_calls": 1,
                        "layer": "ASGI transport with actual PostgreSQL/ECDSA/Reader/Writer/Anvil",
                        "environment_scope": summary["lifecycle_fixture_mode"],
                        "functional_requests_per_minute": 1000,
                        "functional_logins_per_minute": 100,
                        "owned_lifecycle_resources_absent": (
                            True if summary["lifecycle_fixture_mode"] == "FRESH" else None
                        ),
                        "source": f"{W4_QA_SHA}:fixtures/finals/test_w4_lifecycle_qa.py",
                        "time_control": (
                            "trusted API clock and owned EVM timestamp only; OS clock unchanged"
                        ),
                        "not_additive": (
                            "one report group contains 20 core calls and one long "
                            "integration function; not 21 browser tests"
                        ),
                    },
                }
            )
        except Exception as error:
            summary["results"].append(
                {
                    "id": "current_candidate_lifecycle_regression",
                    "status": "FAIL",
                    "error_type": type(error).__name__,
                    "failure_line": traceback.extract_tb(error.__traceback__)[-1].lineno,
                    "observed_issue_errors": lifecycle_errors,
                }
            )
        try:
            output = command(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "packages/python/tests/test_verification.py::test_expired_proof_is_not_reported_as_verified",
                ],
                cwd=product,
            ).decode()
            assert "1 passed" in output
            summary["results"].append(
                {
                    "id": "legacy_v1_expiry",
                    "f_ids": ["F03"],
                    "status": "PASS",
                    "evidence": {
                        "pytest_passed": 1,
                        "expected": "INCONCLUSIVE/EXPIRED/PROOF_EXPIRED",
                        "layer": "deterministic v1 core; not finals-v2 or browser",
                    },
                }
            )
        except Exception as error:
            summary["results"].append(
                {
                    "id": "legacy_v1_expiry",
                    "status": "FAIL",
                    "error_type": type(error).__name__,
                    "failure_line": traceback.extract_tb(error.__traceback__)[-1].lineno,
                }
            )
    except Exception as error:
        summary["setup_error_type"] = type(error).__name__
        summary["setup_failure_line"] = traceback.extract_tb(error.__traceback__)[-1].lineno
        with (out / "diagnostics.log").open("x", encoding="utf-8") as stream:
            (out / "diagnostics.log").chmod(0o600)
            traceback.print_exception(error, file=stream)
    finally:
        try:
            if resources is not None:
                resources.close()
            if env_stack is not None:
                prefix = env_stack["anvil"].removesuffix("-anvil")
                names = set(
                    command(
                        [
                            "docker",
                            "ps",
                            "-a",
                            "--filter",
                            f"name={prefix}",
                            "--format",
                            "{{.Names}}",
                        ]
                    )
                    .decode()
                    .splitlines()
                )
                networks = set(
                    command(
                        [
                            "docker",
                            "network",
                            "ls",
                            "--filter",
                            f"name={prefix}",
                            "--format",
                            "{{.Name}}",
                        ]
                    )
                    .decode()
                    .splitlines()
                )
                containers_absent = not ({prefix + "-pg", prefix + "-anvil"} & names)
                network_absent = prefix not in networks
                summary["resource_absence"] = {
                    "owned_containers_absent": containers_absent,
                    "owned_network_absent": network_absent,
                }
                summary["resources_closed"] = containers_absent and network_absent
            else:
                summary["resource_absence"] = "NOT_CHECKED_BEFORE_YIELD"
        except Exception as error:
            summary["cleanup_error_type"] = type(error).__name__
        private_json(out / "summary.json", summary)
    passed = sum(x["status"] == "PASS" for x in summary["results"])
    failed = sum(x["status"] == "FAIL" for x in summary["results"])
    print(
        json.dumps(
            {
                "report": str(out / "summary.json"),
                "passed": passed,
                "failed": failed,
                "setup_error_type": summary.get("setup_error_type"),
                "browser_e2e": "NOT_RUN",
                "resources_closed": summary["resources_closed"],
            },
            ensure_ascii=False,
        )
    )
    return (
        0
        if passed
        and not failed
        and "setup_error_type" not in summary
        and summary["resources_closed"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
