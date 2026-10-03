"""D W3-D2: opt-in actual HTTP/PostgreSQL/Anvil failures in an owned disposable stack.

No ASGI transport, chain mocks, paid model calls, lifecycle/consume or browser claims.
The root runner provisions/migrates the isolated stack and registers synthetic keys first.
"""

import asyncio
import json
import os
import socket
import subprocess
from contextlib import AsyncExitStack, contextmanager
from datetime import UTC, datetime, timedelta
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import pytest
from originproof_api.database import Database
from sqlalchemy import text

pytestmark = pytest.mark.skipif(
    os.getenv("W3_LIVE_QA") != "1", reason="W3_LIVE_QA=1 disposable actual stack required"
)


def disposable_config():
    assert os.getenv("W3_QA_DISPOSABLE") == "1", "explicit disposable acknowledgement required"
    api_url = os.environ["W3_QA_API_URL"]
    database_url = os.environ["TEST_DATABASE_URL"]
    api, database = urlsplit(api_url), urlsplit(database_url)
    loopback = {"127.0.0.1", "localhost", "::1"}
    assert api.scheme == "http" and api.hostname in loopback
    assert api.port and api.path in ("", "/") and not api.query and not api.fragment
    assert not api.username and not api.password
    assert database.scheme == "postgresql+asyncpg" and database.hostname in loopback
    assert database.port and database.path not in ("", "/")
    signer_directory = Path(os.environ["W3_QA_SIGNER_DIRECTORY"]).resolve()
    assert signer_directory.is_relative_to(Path("/private/tmp"))
    assert signer_directory.is_dir()
    rpc_container = os.environ["W3_QA_RPC_CONTAINER"]
    assert rpc_container.startswith("originproof-w3-d-qa")
    assert all(char.isalnum() or char in "-_" for char in rpc_container)
    inspection = json.loads(
        subprocess.run(
            ["docker", "inspect", rpc_container],
            capture_output=True,
            check=True,
            text=True,
            timeout=15,
        ).stdout
    )[0]
    assert inspection["Config"]["Image"].startswith("ghcr.io/foundry-rs/foundry:")
    assert "anvil" in " ".join([inspection["Path"], *inspection["Args"]])
    assert inspection["State"]["Running"]
    rows = json.loads(Path(os.environ["ORIGINPROOF_TEST_ACCOUNTS"]).read_text())
    accounts = {row["account_id"].removeprefix("acct_"): row for row in rows}
    assert {"bank", "office", "operator", "recipient", "recipient_other", "recipient_new"} <= (
        accounts.keys()
    )
    return api_url.rstrip("/"), database_url, signer_directory, rpc_container, accounts


def issue_body(kind, request_id, recipient_id):
    content = {"proof_type": kind}
    if kind == "PAYMENT_REQUEST":
        content.update(amount_minor=10000, currency="KRW", target_ref="synthetic W3 invoice")
    else:
        content.update(
            institution_code="ORIGIN_MOCK_OFFICE",
            document_type="Certificate",
            document_number="W3-SYNTHETIC-001",
            version=1,
        )
    return {
        "request_id": request_id,
        "recipient_id": recipient_id,
        "expires_at": (datetime.now(UTC).replace(microsecond=0) + timedelta(days=2)).isoformat(),
        "content": content,
    }


async def counts(database, accounts):
    async with database.engine.connect() as connection:
        proof = await connection.scalar(
            text("SELECT count(*) FROM finals_proofs WHERE account_id IN (:bank, :office)"),
            {"bank": accounts["bank"]["account_id"], "office": accounts["office"]["account_id"]},
        )
        audit = await connection.scalar(
            text(
                "SELECT count(*) FROM audit_events WHERE action='issue_proof' "
                "AND actor_account_id IN (:bank, :office)"
            ),
            {"bank": accounts["bank"]["account_id"], "office": accounts["office"]["account_id"]},
        )
        new_token = await connection.scalar(
            text("SELECT count(*) FROM recipient_tokens WHERE account_id=:account"),
            {"account": accounts["recipient_new"]["account_id"]},
        )
        return proof, audit, new_token


def assert_result(response, status, scope):
    assert response.status_code == 200
    result = response.json()
    assert result["verification_status"] == status
    assert result["scope"] == scope
    assert result["lifecycle_status"] is None
    assert result["checks"]["proof_status"] == "NOT_RUN"
    return result


@contextmanager
def response_loss_relay(api_url):
    """Forward one actual issuance, then close the caller connection after its response."""
    upstream = urlsplit(api_url)
    completed = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            if self.path != "/v2/issuer/proofs":
                self.send_error(404)
                return
            body = self.rfile.read(int(self.headers["Content-Length"]))
            headers = {
                name: self.headers[name]
                for name in ("Content-Type", "Cookie", "X-CSRF-Token")
                if name in self.headers
            }
            connection = HTTPConnection(upstream.hostname, upstream.port, timeout=20)
            try:
                connection.request("POST", self.path, body=body, headers=headers)
                response = connection.getresponse()
                response.read()
                completed.append(response.status)
                self.close_connection = True
                self.connection.shutdown(socket.SHUT_RDWR)
            finally:
                connection.close()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", completed
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


async def test_w3_actual_http_permissions_failures_and_atomic_storage():
    api_url, database_url, signers, rpc_container, accounts = disposable_config()
    database = Database(database_url)
    suffix = uuid4().hex[:12]
    clients = {}
    try:
        async with AsyncExitStack() as stack:
            for role in (*accounts, "anonymous"):
                client = await stack.enter_async_context(
                    httpx.AsyncClient(base_url=api_url, timeout=20, trust_env=False)
                )
                clients[role] = client
                if role != "anonymous":
                    row = accounts[role]
                    login = await client.post(
                        "/v1/auth/login",
                        json={"username": row["username"], "password": row["password"]},
                    )
                    assert login.status_code == 200
                    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
            bank, office = clients["bank"], clients["office"]
            anonymous, recipient = clients["anonymous"], clients["recipient"]
            baseline = await counts(database, accounts)
            assert baseline[2] == 0, "recipient_new must have no pre-existing token"
            body = issue_body(
                "PAYMENT_REQUEST", f"req_qa_denied_{suffix}", accounts["recipient"]["account_id"]
            )
            for role, status in (("anonymous", 401), ("operator", 403), ("recipient", 403)):
                response = await clients[role].post("/v2/issuer/proofs", json=body)
                assert response.status_code == status
            response = await bank.post(
                "/v2/issuer/proofs", json=body, headers={"X-CSRF-Token": "synthetic-wrong"}
            )
            assert response.status_code == 403
            for field in ("issuer_id", "key_id", "nonce", "role"):
                response = await bank.post(
                    "/v2/issuer/proofs", json=body | {field: "synthetic-injection"}
                )
                assert response.status_code == 422
            wrong_type = issue_body(
                "OFFICIAL_DOCUMENT", body["request_id"], accounts["recipient"]["account_id"]
            )
            assert (await bank.post("/v2/issuer/proofs", json=wrong_type)).status_code == 403
            wrong_code = wrong_type | {
                "content": wrong_type["content"] | {"institution_code": "OTHER_SYNTHETIC"}
            }
            assert (await office.post("/v2/issuer/proofs", json=wrong_code)).status_code == 422
            assert (
                await bank.post(
                    "/v2/issuer/proofs",
                    json=body | {"recipient_id": accounts["operator"]["account_id"]},
                )
            ).status_code == 422
            assert await counts(database, accounts) == baseline

            issued = []
            for role, kind in (("bank", "PAYMENT_REQUEST"), ("office", "OFFICIAL_DOCUMENT")):
                issuer = clients[role]
                body = issue_body(
                    kind, f"req_qa_issue_{role}_{suffix}", accounts["recipient"]["account_id"]
                )
                before = await counts(database, accounts)
                async with httpx.AsyncClient(
                    base_url=api_url,
                    cookies=issuer.cookies,
                    headers=issuer.headers,
                    timeout=20,
                    trust_env=False,
                ) as second:
                    first, retry = await asyncio.gather(
                        issuer.post("/v2/issuer/proofs", json=body),
                        second.post("/v2/issuer/proofs", json=body),
                    )
                assert first.status_code == retry.status_code == 200
                assert first.json() == retry.json()
                proof_id = first.json()["proof_id"]
                after = await counts(database, accounts)
                assert after == (before[0] + 1, before[1] + 1, before[2])
                conflict = body | {"recipient_id": accounts["recipient_other"]["account_id"]}
                assert (await issuer.post("/v2/issuer/proofs", json=conflict)).status_code == 409
                protected = await recipient.get(f"/v2/proofs/{proof_id}/content")
                assert protected.status_code == 200
                envelope = protected.json()["envelope"]
                async with database.engine.connect() as connection:
                    rows = (
                        await connection.execute(
                            text(
                                "SELECT envelope FROM finals_proofs "
                                "WHERE account_id=:account AND request_id=:request"
                            ),
                            {
                                "account": accounts[role]["account_id"],
                                "request": body["request_id"],
                            },
                        )
                    ).all()
                    assert len(rows) == 1
                    assert rows[0][0] == envelope
                    assert (
                        await connection.scalar(
                            text(
                                "SELECT count(*) FROM audit_events WHERE target_id=:proof "
                                "AND action='issue_proof'"
                            ),
                            {"proof": proof_id},
                        )
                        == 1
                    )
                public = await anonymous.get(f"/v2/proofs/{proof_id}")
                assert public.status_code == 200
                assert set(public.json()) == {
                    "proof_id",
                    "issuer_id",
                    "key_id",
                    "proof_type",
                    "schema_version",
                    "issued_at",
                    "expires_at",
                    "verification_path",
                }
                query = {"request_id": f"req_qa_verify_{suffix}"}
                result = assert_result(
                    await anonymous.post(f"/v2/proofs/{proof_id}/verify", json=query),
                    "VERIFIED",
                    "PROOF_ONLY",
                )
                assert result["checks"]["candidate_match"] == "NOT_RUN"
                candidate = {
                    key: value for key, value in body["content"].items() if key != "proof_type"
                }
                result = assert_result(
                    await recipient.post(
                        f"/v2/proofs/{proof_id}/verify", json=query | {"candidate": candidate}
                    ),
                    "VERIFIED",
                    "FULL_COMPARISON",
                )
                field = "amount_minor" if role == "bank" else "document_number"
                changed = 10001 if role == "bank" else "W3-CHANGED"
                result = assert_result(
                    await recipient.post(
                        f"/v2/proofs/{proof_id}/verify",
                        json=query | {"candidate": candidate | {field: changed}},
                    ),
                    "TAMPERED",
                    "FULL_COMPARISON",
                )
                assert ("AMOUNT_MISMATCH" if role == "bank" else "FIELD_MISMATCH") in (
                    result["reason_codes"]
                )
                missing = {key: value for key, value in candidate.items() if key != field}
                result = assert_result(
                    await recipient.post(
                        f"/v2/proofs/{proof_id}/verify", json=query | {"candidate": missing}
                    ),
                    "INCONCLUSIVE",
                    "PARTIAL_COMPARISON",
                )
                assert "INPUT_INCOMPLETE" in result["reason_codes"]
                for denied_role, status in (
                    ("anonymous", 401),
                    ("operator", 404),
                    ("recipient_other", 404),
                    ("office" if role == "bank" else "bank", 404),
                ):
                    denied = clients[denied_role]
                    assert (
                        await denied.get(f"/v2/proofs/{proof_id}/content")
                    ).status_code == status
                    response = await denied.post(
                        f"/v2/proofs/{proof_id}/verify", json=query | {"candidate": candidate}
                    )
                    assert response.status_code == status
                other = clients["office" if role == "bank" else "bank"]
                listing = await other.get("/v2/issuer/proofs")
                assert listing.status_code == 200
                assert proof_id not in {row["proof_id"] for row in listing.json()}
                assert await counts(database, accounts) == after
                issued.append((proof_id, body))

            # Fail before signing without deleting or losing the original owned synthetic key.
            async with database.engine.connect() as connection:
                reference = await connection.scalar(
                    text(
                        "SELECT secret_ref FROM issuer_keys WHERE issuer_id=:issuer "
                        "AND selected=true"
                    ),
                    {"issuer": "iss_origin_mock_bank"},
                )
            assert reference and Path(reference).name == reference
            signer = signers / reference
            backup = signers / f"{reference}.w3-qa-backup-{suffix}"
            before = await counts(database, accounts)
            signer.rename(backup)
            try:
                for present in (False, True):
                    if present:
                        signer.touch(mode=0o600)
                        signer.write_bytes(bytes.fromhex("11" * 32))
                    failed = issue_body(
                        "PAYMENT_REQUEST",
                        f"req_qa_signer_{present}_{suffix}",
                        accounts["recipient"]["account_id"],
                    )
                    response = await bank.post("/v2/issuer/proofs", json=failed)
                    assert response.status_code == 409
                    assert response.json()["detail"] == "ISSUING_KEY_UNAVAILABLE"
                    assert await counts(database, accounts) == before
            finally:
                if signer.exists():
                    signer.unlink()
                backup.rename(signer)

            # A deferred real PostgreSQL trigger fails at commit, after all rows are flushed.
            request_id = f"req_qa_commit_{suffix}"
            function = f"w3_qa_commit_fail_{suffix}"
            trigger = f"w3_qa_commit_trigger_{suffix}"
            async with database.engine.begin() as connection:
                await connection.execute(
                    text(
                        f"CREATE FUNCTION {function}() RETURNS trigger LANGUAGE plpgsql AS $$ "
                        "BEGIN IF NEW.request_id=TG_ARGV[0] THEN "
                        "RAISE EXCEPTION 'synthetic QA commit failure'; END IF; RETURN NEW; END $$"
                    )
                )
                await connection.execute(
                    text(
                        f"CREATE CONSTRAINT TRIGGER {trigger} AFTER INSERT ON finals_proofs "
                        f"DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
                        f"EXECUTE FUNCTION {function}('{request_id}')"
                    )
                )
            body = issue_body(
                "PAYMENT_REQUEST", request_id, accounts["recipient_new"]["account_id"]
            )
            before = await counts(database, accounts)
            try:
                response = await bank.post("/v2/issuer/proofs", json=body)
                assert response.status_code == 500
                assert await counts(database, accounts) == before
                async with database.engine.connect() as connection:
                    assert (
                        await connection.scalar(
                            text("SELECT count(*) FROM finals_proofs WHERE request_id=:request"),
                            {"request": request_id},
                        )
                        == 0
                    )
            finally:
                async with database.engine.begin() as connection:
                    await connection.execute(text(f"DROP TRIGGER {trigger} ON finals_proofs"))
                    await connection.execute(text(f"DROP FUNCTION {function}()"))
            assert (await bank.post("/v2/issuer/proofs", json=body)).status_code == 200
            assert await counts(database, accounts) == (before[0] + 1, before[1] + 1, 1)

            # Stop/start only the named owned Anvil; no preserved database/service is touched.
            before = await counts(database, accounts)
            try:
                await asyncio.to_thread(
                    subprocess.run,
                    ["docker", "stop", "--time", "1", rpc_container],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=20,
                )
                failed = issue_body(
                    "PAYMENT_REQUEST", f"req_qa_rpc_{suffix}", accounts["recipient"]["account_id"]
                )
                response = await bank.post("/v2/issuer/proofs", json=failed)
                assert response.status_code == 503
                assert response.json()["detail"] == "CHAIN_UNAVAILABLE"
                result = assert_result(
                    await anonymous.post(
                        f"/v2/proofs/{issued[0][0]}/verify",
                        json={"request_id": f"req_qa_outage_{suffix}"},
                    ),
                    "INCONCLUSIVE",
                    "PROOF_ONLY",
                )
                assert result["reason_codes"] == ["DEPENDENCY_UNAVAILABLE"]
                assert await counts(database, accounts) == before
            finally:
                await asyncio.to_thread(
                    subprocess.run,
                    ["docker", "start", rpc_container],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=20,
                )
            recovered = None
            for _ in range(20):
                recovered = await anonymous.post(
                    f"/v2/proofs/{issued[0][0]}/verify",
                    json={"request_id": f"req_qa_recovered_{suffix}"},
                )
                if recovered.status_code == 200 and (
                    recovered.json()["verification_status"] == "VERIFIED"
                ):
                    break
                await asyncio.sleep(0.5)
            assert_result(recovered, "VERIFIED", "PROOF_ONLY")

            # Drop only the HTTP response after real signing/storage; retry must reuse it.
            body = issue_body(
                "PAYMENT_REQUEST",
                f"req_qa_response_loss_{suffix}",
                accounts["recipient"]["account_id"],
            )
            before = await counts(database, accounts)
            with response_loss_relay(api_url) as (relay_url, completed):
                async with httpx.AsyncClient(
                    base_url=relay_url,
                    cookies=bank.cookies,
                    headers=bank.headers,
                    timeout=20,
                    trust_env=False,
                ) as lost:
                    with pytest.raises(httpx.HTTPError):
                        await lost.post("/v2/issuer/proofs", json=body)
                assert completed == [200]
            retry = await bank.post("/v2/issuer/proofs", json=body)
            assert retry.status_code == 200
            proof_id = retry.json()["proof_id"]
            assert await counts(database, accounts) == (before[0] + 1, before[1] + 1, before[2])
            protected = await recipient.get(f"/v2/proofs/{proof_id}/content")
            assert protected.status_code == 200
            assert_result(
                await recipient.post(
                    f"/v2/proofs/{proof_id}/verify",
                    json={
                        "request_id": f"req_qa_final_{suffix}",
                        "candidate": {
                            key: value
                            for key, value in body["content"].items()
                            if key != "proof_type"
                        },
                    },
                ),
                "VERIFIED",
                "FULL_COMPARISON",
            )
    finally:
        await database.dispose()
