"""Real PostgreSQL/HTTP/API-process recovery; Registry and analyzer evidence is synthetic.

V5_C_LIVE_TEST=1 make test-v5-c-live. Only per-test containers/databases are modified.
The factory below is exclusively for these tests, never a production composition root.
"""

import asyncio
import base64
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from eth_keys import keys
from originproof_api.accounts import password_hash
from originproof_api.database import (
    AccountRow,
    AuditEventRow,
    Database,
    IssuerApplicationRow,
    OperationRow,
    SignedProofRow,
)
from originproof_api.main import create_app
from originproof_api.operations import input_fingerprint
from originproof_api.settings import Settings
from originproof_api.wallet_database import WalletAnalysisRow, WalletInputRow, WalletSigningRow
from originproof_api.wallet_runtime import WalletRuntime
from originproof_core import DependencyUnavailableError
from originproof_core.wallet_contract import DocumentView, SigningRequest
from originproof_core.wallet_ports import WalletDocument
from originproof_core.wallet_signatures import identifier_hash, wallet_digest, wallet_signer
from sqlalchemy import func, select, text
from test_w6_c_recovery import LiveState, command, port, wait_http

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    os.getenv("V5_C_LIVE_TEST") != "1", reason="v5 disposable live opt-in"
)
ISSUER = "iss_origin_mock_bank"
ISSUER_HASH = identifier_hash(ISSUER)
KEY_ID = identifier_hash("v5_c_live_key")
SIGNER = keys.PrivateKey((1).to_bytes(32, "big")).public_key.to_checksum_address().lower()
POSITION = {
    "chain_id": "31337",
    "verifying_contract": "0x" + "12" * 20,
    "block_number": "10",
    "block_hash": "0x" + "ab" * 32,
}


def write_state(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value))
    temporary.replace(path)


class SyntheticRegistry:
    def __init__(self, directory):
        self.directory = directory

    def read(self):
        state = json.loads((self.directory / "chain.json").read_text())
        if state.get("offline"):
            raise DependencyUnavailableError("synthetic unavailable")
        return state

    async def issuer(self, identifier):
        return self.read()["issuers"].get(identifier)

    async def key(self, identifier):
        return self.read()["keys"].get(identifier)

    async def is_approver(self, address):
        return address == "0x" + "23" * 20

    async def proposal(self, identifier):
        return None

    async def document(self, identifier, version):
        rows = [d for d in self.read()["documents"] if d["document"]["document_id"] == identifier]
        if version is None:
            return max(rows, key=lambda d: d["document"]["version"], default=None)
        return next((d for d in rows if d["document"]["version"] == version), None)

    async def transaction(self, tx_hash):
        return self.read()["transactions"].get(tx_hash)

    async def find_transaction(self, intent):
        return next(
            (
                t
                for t in self.read()["transactions"].values()
                if t["action"] == intent["action"] and t["arguments"] == intent["arguments"]
            ),
            None,
        )

    async def submit(self, signing, signature):
        with (self.directory / "submissions.jsonl").open("a") as output:
            output.write(
                json.dumps(
                    {"message": signing.message.model_dump(by_alias=True), "signature": signature}
                )
                + "\n"
            )
        await asyncio.Event().wait()  # Simulate an external send followed by a lost response.


def process_app():
    if os.environ.get("V5_C_LIVE_TEST") != "1":
        raise RuntimeError("this factory is a synthetic live-test fixture")
    directory = Path(os.environ["V5_C_TEST_DIRECTORY"])
    settings = Settings(
        _env_file=None,
        database_url=os.environ["API_DATABASE_URL"],
        blockchain_chain_id=31337,
        wallet_registry_address=POSITION["verifying_contract"],
        wallet_internal_approvers={ISSUER: "acct_internal"},
        wallet_demo_email_enabled=True,
        wallet_email_secret="synthetic-server-email-secret-for-disposable-live-tests",
        wallet_text_input_enabled=True,
        wallet_relay_enabled=os.environ.get("V5_C_RELAY") == "1",
        finals_payment_issuer_id=ISSUER,
        finals_document_issuer_id="iss_origin_mock_office",
        signer_directory=str(directory / "issuer-signers-must-not-exist"),
        projection_enabled=False,
        requests_per_minute=1000,
        logins_per_minute=100,
    )

    async def processor(value):
        def completed(_):
            with (directory / "finished-analyses.jsonl").open("a") as output:
                output.write("finished\n")

        asyncio.current_task().add_done_callback(completed)
        with (directory / "analyses.jsonl").open("a") as output:
            output.write("accepted\n")
        mode = (directory / "analysis-mode").read_text()
        if mode == "hold":
            while not (directory / "release").exists():
                await asyncio.sleep(0.02)
        return {
            "risk_level": "CAUTION",
            "evidence": [
                {
                    "rule_id": "SYNTHETIC",
                    "quote": value[:3],
                    "start_offset": 0,
                    "end_offset": 3,
                    "source": "RULE",
                }
            ],
            "limitations": ["synthetic processor"],
            "verification_not_run_reason": "NO_DOCUMENT_REFERENCE",
        }

    return create_app(
        settings=settings, wallet_chain=SyntheticRegistry(directory), analysis_processor=processor
    )


async def until(predicate, *, timeout=10):
    async with asyncio.timeout(timeout):
        while True:
            result = await predicate()
            if result:
                return result
            await asyncio.sleep(0.03)


@pytest.fixture
async def wallet_live(tmp_path):
    name = "originproof-v5-c-" + uuid4().hex[:12]
    api_port, pg_port = port(), port()
    db_url = f"postgresql+asyncpg://originproof:originproof@127.0.0.1:{pg_port}/originproof"
    env = os.environ | {
        "V5_C_LIVE_TEST": "1",
        "V5_C_RELAY": "0",
        "V5_C_TEST_DIRECTORY": str(tmp_path),
        "API_DATABASE_URL": db_url,
        "PYTHONPATH": os.pathsep.join(
            str(ROOT / p)
            for p in ("apps/api/src", "packages/python", "services/indexer/src", "scripts/ci")
        ),
    }
    env.pop("OPENAI_API_KEY", None)
    state = {"issuers": {}, "keys": {}, "documents": [], "transactions": {}}
    write_state(tmp_path / "chain.json", state)
    (tmp_path / "analysis-mode").write_text("normal")
    process, database, clients, created = None, None, [], False

    def stop():
        nonlocal process
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        process = None

    def start():
        nonlocal process
        assert process is None
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "test_v5_c_recovery:process_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
                "--no-proxy-headers",
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    async def login(username):
        client = httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{api_port}", timeout=20, trust_env=False
        )
        clients.append(client)
        result = await client.post(
            "/v1/auth/login", json={"username": username, "password": "synthetic-v5-process-check"}
        )
        assert result.status_code == 200, result.text
        client.headers["X-CSRF-Token"] = result.json()["csrf_token"]
        return client

    def migrate(target):
        command(
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "apps/api/alembic.ini",
            "upgrade",
            target,
            cwd=ROOT,
            env=env,
        )

    try:
        command(
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--label",
            "originproof.validation=true",
            "--tmpfs",
            "/var/lib/postgresql/data",
            "-p",
            f"127.0.0.1:{pg_port}:5432",
            "-e",
            "POSTGRES_USER=originproof",
            "-e",
            "POSTGRES_PASSWORD=originproof",
            "-e",
            "POSTGRES_DB=originproof",
            "postgres:16.4-alpine",
        )
        created = True
        for _ in range(100):
            if (
                subprocess.run(
                    ["docker", "exec", name, "pg_isready", "-U", "originproof"], capture_output=True
                ).returncode
                == 0
            ):
                break
            await asyncio.sleep(0.1)
        else:
            raise AssertionError("disposable PostgreSQL did not start")
        migrate("20261003_0006")
        database = Database(db_url)
        hashed = password_hash("synthetic-v5-process-check")
        async with database.session_factory() as db:
            for username, role, issuer in (
                ("bank", "issuer", ISSUER),
                ("bank_other", "issuer", ISSUER),
                ("internal", "issuer", ISSUER),
                ("office", "issuer", "iss_origin_mock_office"),
                ("operator", "operator", None),
                ("recipient", "recipient", None),
            ):
                db.add(
                    AccountRow(
                        account_id="acct_" + username,
                        username=username,
                        role=role,
                        issuer_id=issuer,
                        password_hash=hashed,
                    )
                )
            await db.flush()
            db.add(
                IssuerApplicationRow(
                    application_id="app_live",
                    issuer_id=ISSUER,
                    applicant_account_id="acct_bank",
                    issuer_name="Origin Mock Bank",
                    status="PENDING_REVIEW",
                )
            )
            legacy = json.loads(
                (ROOT / "fixtures/golden/card_payment_notice_signing_v1.json").read_text()
            )
            db.add(
                SignedProofRow(
                    proof_id="proof_v5_restore_sentinel",
                    issuer_id="iss_legacy",
                    key_id="key_legacy",
                    payload_hash=legacy["payload_hash"],
                    envelope=legacy,
                )
            )
            await db.commit()
        migrate("head")
        start()
        url = f"http://127.0.0.1:{api_port}"
        await wait_http(url + "/health/ready")
        bank, internal, recipient = (
            await login("bank"),
            await login("internal"),
            await login("recipient"),
        )
        issued = await bank.post(
            "/v3/issuer-applications/app_live/email-codes",
            json={"email": "staff@bank.example.invalid"},
        )
        assert issued.status_code == 201, issued.text
        code = (await bank.get("/v3/issuer-applications/app_live/demo-inbox")).json()["code"]
        assert (
            await bank.post(
                "/v3/issuer-applications/app_live/email-verifications", json={"code": code}
            )
        ).status_code == 200
        approved = await internal.post(
            "/v3/issuer-applications/app_live/internal-approvals",
            json={"decision": "APPROVE", "reason": "synthetic"},
        )
        assert approved.status_code == 200, approved.text
        state["issuers"][ISSUER_HASH] = POSITION | {
            "issuer_id": ISSUER_HASH,
            "state": "ACTIVE",
            "key_id": KEY_ID,
            "signer": SIGNER,
            "metadata_hash": approved.json()["metadata_hash"],
            "next_nonce": "0",
            "governance_nonce": "1",
        }
        state["keys"][KEY_ID] = POSITION | {
            "key_id": KEY_ID,
            "issuer_id": ISSUER_HASH,
            "signer": SIGNER,
            "registered_block": "2",
        }
        write_state(tmp_path / "chain.json", state)
        yield LiveState(
            tmp=tmp_path,
            name=name,
            env=env,
            state=state,
            database=database,
            bank=bank,
            recipient=recipient,
            start=start,
            stop=stop,
            login=login,
            url=url,
            legacy=legacy,
        )
    finally:
        stop()
        for client in clients:
            await client.aclose()
        if database is not None:
            await database.dispose()
        if created:
            command("docker", "rm", "-f", name)


def signed(value):
    model = SigningRequest.model_validate(value)
    signature = (
        keys.PrivateKey((1).to_bytes(32, "big"))
        .sign_msg_hash(bytes.fromhex(wallet_digest(model.domain, model.message)[2:]))
        .to_bytes()
    )
    return "0x" + (signature[:64] + bytes([signature[64] + 27])).hex()


async def draft(live, request_id="req_draft", version=1, *, client=None):
    result = await (client or live.bank).post(
        "/v3/document-drafts",
        json={
            "request_id": request_id,
            "doc_key": identifier_hash("v5_live_document"),
            "expected_version": version,
            "expires_at": int(time.time()) + 86400,
            "content": {
                "notice_type": "PAYMENT_REQUEST",
                "amount_minor": 154000,
                "currency": "KRW",
                "payee_bank_name": "합성 은행",
                "payee_account_number": "001234567890",
                "payee_account_holder": "합성 기관",
                "payment_purpose": "합성 안내",
                "due_at": int(time.time()) + 3600,
                "official_url": "https://bank.example.invalid",
            },
        },
    )
    assert result.status_code == 201, result.text
    return result.json()


def confirm_on_synthetic_chain(live, signing):
    message = SigningRequest.model_validate(signing).message
    fields = {
        name: getattr(message, name)
        for name in (
            "document_id",
            "issuer_id",
            "doc_key",
            "key_id",
            "version",
            "original_hash",
            "protected_hash",
            "content_schema",
            "issued_at",
            "expires_at",
        )
    }
    for old in live.state["documents"]:
        if old["document"]["document_id"] == message.document_id:
            document = old["document"]
            if document["version"] == message.version - 1 and document["state"] == "ACTIVE":
                document["state"] = "SUPERSEDED"
            document["latest_version"] = message.version
    record = WalletDocument(
        **POSITION,
        document=DocumentView(
            **fields,
            latest_version=message.version,
            state="ACTIVE",
            warnings=[],
            original_available=False,
        ),
        published_at=message.issued_at,
        published_block="10",
    )
    live.state["documents"].append(record.model_dump(mode="json"))
    live.state["issuers"][ISSUER_HASH]["next_nonce"] = str(int(message.nonce) + 1)
    tx_hash = "0x" + f"{message.version:02x}" * 32
    live.state["transactions"][tx_hash] = POSITION | {
        "tx_hash": tx_hash,
        "sender": "0x" + "23" * 20,
        "action": "Publish",
        "status": "CONFIRMED",
        "arguments": {"message": signing["message"], "signature": signed(signing)},
    }
    write_state(live.tmp / "chain.json", live.state)
    return tx_hash


async def publish(live, signing, request_id="req_publish"):
    response = await live.bank.post(
        "/v3/publications",
        json={
            "request_id": request_id,
            "signing_request_id": signing["signing_request_id"],
            "signature": signed(signing),
        },
    )
    assert response.status_code == 202, response.text
    tx_hash = confirm_on_synthetic_chain(live, signing)
    confirmed = await live.bank.post(
        f"/v3/signing-requests/{signing['signing_request_id']}/transactions",
        json={
            "request_id": "req_tx_" + request_id,
            "signing_request_id": signing["signing_request_id"],
            "tx_hash": tx_hash,
        },
    )
    assert confirmed.status_code == 202 and confirmed.json()["status"] == "CONFIRMED", (
        confirmed.text
    )
    return confirmed.json()


async def analyze(live, *, request_id="req_analysis", **options):
    source = await live.recipient.post(
        "/v3/inputs", json={"kind": "TEXT", "text": "💡공식 창구를 확인하세요"}
    )
    assert source.status_code == 201, source.text
    body = {"request_id": request_id, "input_ref": source.json()["input_ref"], **options}
    response = await live.recipient.post("/v3/analyses", json=body)
    assert response.status_code == 202, response.text
    return body, response.json()["analysis_id"]


async def analysis_status(live, analysis_id, status):
    response = await live.recipient.get(f"/v3/analyses/{analysis_id}")
    assert response.status_code == 200, response.text
    return response.json() if response.json()["status"] == status else None


async def test_v5_backup_restore_preserves_original_signature_analysis_and_legacy(wallet_live):
    live = wallet_live
    first = await draft(live)
    operation = await publish(live, first)
    alias = {
        "request_id": "req_restore_alias",
        "signing_request_id": first["signing_request_id"],
        "signature": signed(first),
    }
    retries = await asyncio.gather(
        *(live.bank.post("/v3/publications", json=alias) for _ in range(2))
    )
    for retry in retries:
        assert retry.status_code == 202, retry.text
        assert retry.json()["operation_id"] == operation["operation_id"]
    old = live.state["documents"][0]["document"]
    old["state"] = "REVOKED"
    revoked = dict(old)
    second = await draft(live, "req_second", 2)
    await publish(live, second, "req_publish_second")
    assert old == revoked | {"latest_version": 2}
    _, analysis_id = await analyze(live, retain_report=True, retain_original=True)
    report = await until(lambda: analysis_status(live, analysis_id, "COMPLETED"))
    did = first["message"]["documentId"]
    material = (await live.bank.get(f"/v3/documents/{did}/verification-material?version=1")).json()
    live.stop()
    dump = command(
        "docker", "exec", live.name, "pg_dump", "-U", "originproof", "-Fc", "originproof"
    )
    backup = live.tmp / "database.dump"
    backup.touch(mode=0o600)
    backup.write_bytes(dump)
    assert backup.stat().st_mode & 0o777 == 0o600
    command("docker", "exec", live.name, "createdb", "-U", "originproof", "originproof_restore")
    command(
        "docker",
        "exec",
        "-i",
        live.name,
        "pg_restore",
        "--exit-on-error",
        "--no-owner",
        "-U",
        "originproof",
        "-d",
        "originproof_restore",
        input=dump,
    )
    live.env["API_DATABASE_URL"] = (
        live.env["API_DATABASE_URL"].removesuffix("originproof") + "originproof_restore"
    )
    restored = Database(live.env["API_DATABASE_URL"])
    try:
        command(
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "apps/api/alembic.ini",
            "check",
            cwd=ROOT,
            env=live.env,
        )
        async with restored.session_factory() as db:
            assert (
                await db.get(SignedProofRow, "proof_v5_restore_sentinel")
            ).envelope == live.legacy
        live.start()
        await wait_http(live.url + "/health/ready")
        bank = await live.login("bank")
        retry = await bank.post("/v3/publications", json=alias)
        assert (
            retry.status_code == 202 and retry.json()["operation_id"] == operation["operation_id"]
        )
        conflict = await bank.post(
            "/v3/publications",
            json={
                **alias,
                "signing_request_id": second["signing_request_id"],
                "signature": signed(second),
            },
        )
        assert conflict.status_code == 409 and conflict.json()["detail"] == "REQUEST_ID_CONFLICT"
        assert (
            await bank.get(f"/v3/documents/{did}/verification-material?version=1")
        ).json() == material
        assert (await live.recipient.get(f"/v3/analyses/{analysis_id}")).json() == report
        raw = await live.recipient.get(f"/v3/analyses/{analysis_id}/original")
        assert raw.status_code == 200 and raw.text == "💡공식 창구를 확인하세요"
        signing = SigningRequest.model_validate(material["signing_request"])
        assert wallet_signer(signing.domain, signing.message, material["signature"]) == SIGNER
        assert (
            "0x" + hashlib.sha256(base64.b64decode(signing.original_base64)).hexdigest()
            == signing.message.original_hash
        )
        assert not (live.tmp / "issuer-signers-must-not-exist").exists()
    finally:
        await restored.dispose()


async def test_v5_actual_kill_unknown_and_receipt_db_failure_never_resend(wallet_live):
    live = wallet_live
    signing = await draft(live)
    body = {
        "request_id": "req_crash",
        "signing_request_id": signing["signing_request_id"],
        "signature": signed(signing),
    }
    live.stop()
    live.env["V5_C_RELAY"] = "1"
    live.start()
    await wait_http(live.url + "/health/ready")
    submitting = asyncio.create_task(live.bank.post("/v3/publications", json=body))

    async def sent():
        path = live.tmp / "submissions.jsonl"
        return path.exists() and path.read_text().endswith("\n")

    await until(sent)
    live.stop()
    with pytest.raises(httpx.HTTPError):
        await submitting
    async with live.database.session_factory() as db:
        row = await db.scalar(select(OperationRow).where(OperationRow.request_id == "req_crash"))
        operation = row.operation_id
        assert row.status == "UNKNOWN"
        source = await db.get(WalletSigningRow, signing["signing_request_id"])
        assert (
            source.signature == body["signature"]
            and source.payload["original_base64"] == signing["original_base64"]
        )
    live.start()
    await wait_http(live.url + "/health/ready")
    retry = await live.bank.post("/v3/publications", json=body)
    assert retry.json()["operation_id"] == operation and retry.json()["status"] == "UNKNOWN"
    path = f"/v3/operations/{operation}/reconcile"
    assert (await live.bank.post(path)).json()["status"] == "UNKNOWN"
    confirm_on_synthetic_chain(live, signing)
    async with live.database.session_factory() as db:
        await db.execute(
            text(
                "CREATE FUNCTION reject_wallet_material() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'synthetic commit failure'; END $$"
            )
        )
        await db.execute(
            text(
                "CREATE TRIGGER reject_wallet_material BEFORE INSERT ON wallet_document_versions "
                "FOR EACH ROW EXECUTE FUNCTION reject_wallet_material()"
            )
        )
        await db.commit()
    assert (await live.bank.post(path)).status_code == 500
    live.stop()
    async with live.database.session_factory() as db:
        assert (await db.get(OperationRow, operation)).status == "UNKNOWN"
        await db.execute(text("DROP TRIGGER reject_wallet_material ON wallet_document_versions"))
        await db.execute(text("DROP FUNCTION reject_wallet_material()"))
        await db.commit()
    live.start()
    await wait_http(live.url + "/health/ready")
    confirmed = await live.bank.post(path)
    assert confirmed.status_code == 202 and confirmed.json()["status"] == "CONFIRMED", (
        confirmed.text
    )
    assert len((live.tmp / "submissions.jsonl").read_text().splitlines()) == 1


async def test_v5_actual_worker_restart_resume_and_late_result_deletion(wallet_live):
    live = wallet_live
    (live.tmp / "analysis-mode").write_text("hold")
    body, analysis_id = await analyze(live)
    await until(lambda: analysis_status(live, analysis_id, "RUNNING"))
    live.stop()
    live.start()
    await wait_http(live.url + "/health/ready")
    failed = await until(lambda: analysis_status(live, analysis_id, "FAILED"))
    assert failed["error_code"] == "PROCESS_RESTARTED"
    assert (await live.recipient.post("/v3/analyses", json=body)).json()[
        "analysis_id"
    ] == analysis_id
    async with live.database.session_factory() as db:
        assert (await db.get(WalletInputRow, body["input_ref"])).original is None
    live.stop()
    queued_body = {"request_id": "req_queued", "input_ref": "inp_queued"}
    async with live.database.session_factory() as db:
        stamp = int(time.time())
        db.add(
            WalletInputRow(
                input_id="inp_queued",
                account_id="acct_recipient",
                kind="TEXT",
                original="합성 대기 자료".encode(),
                accepted_at=stamp,
                expires_at=stamp + 3600,
            )
        )
        await db.flush()
        db.add(
            WalletAnalysisRow(
                analysis_id="ana_queued",
                account_id="acct_recipient",
                input_id="inp_queued",
                request_id="req_queued",
                input_hash=input_fingerprint(queued_body),
                status="QUEUED",
                accepted_at=stamp,
                retain_report=False,
                retain_original=False,
            )
        )
        await db.commit()
    (live.tmp / "analysis-mode").write_text("normal")
    live.start()
    await wait_http(live.url + "/health/ready")
    await until(lambda: analysis_status(live, "ana_queued", "COMPLETED"))
    assert len((live.tmp / "analyses.jsonl").read_text().splitlines()) == 2
    (live.tmp / "analysis-mode").write_text("hold")
    _, late_id = await analyze(
        live, request_id="req_delete_late", retain_report=True, retain_original=True
    )
    await until(lambda: analysis_status(live, late_id, "RUNNING"))
    assert (await live.recipient.delete(f"/v3/analyses/{late_id}")).status_code == 204
    (live.tmp / "release").touch()

    async def finished():
        path = live.tmp / "finished-analyses.jsonl"
        return path.exists() and len(path.read_text().splitlines()) == 2

    await until(finished)
    assert (await live.recipient.get(f"/v3/analyses/{late_id}")).json()["status"] == "CANCELLED"
    async with live.database.session_factory() as db:
        assert (await db.get(WalletAnalysisRow, late_id)).report is None


async def test_v5_postgres_competing_next_versions_and_http_security(wallet_live):
    live = wallet_live
    published = await draft(live)
    await publish(live, published)
    other = await live.login("bank_other")
    first = await draft(live, "req_compete_a", 2)
    second = await draft(live, "req_compete_b", 2, client=other)
    candidates = [(live.bank, first), (other, second)]
    results = await asyncio.gather(
        *(
            client.post(
                "/v3/publications",
                json={
                    "request_id": "req_race_" + str(i),
                    "signing_request_id": value["signing_request_id"],
                    "signature": signed(value),
                },
            )
            for i, (client, value) in enumerate(candidates)
        )
    )
    assert sorted(r.status_code for r in results) == [202, 409], [r.text for r in results]
    success = next(r.json() for r in results if r.status_code == 202)
    async with live.database.session_factory() as db:
        pending = await db.scalar(
            select(func.count())
            .select_from(OperationRow)
            .where(
                OperationRow.action == "wallet_publish", OperationRow.status == "PENDING_SUBMISSION"
            )
        )
        assert pending == 1
    assert (
        await live.recipient.get(f"/v3/operations/{success['operation_id']}")
    ).status_code == 404
    assert (
        await live.bank.post(
            "/v3/inputs", json={"kind": "TEXT", "text": "합성"}, headers={"X-CSRF-Token": "wrong"}
        )
    ).status_code == 403
    assert (await live.bank.post("/v3/inputs", content=b"x" * 65537)).status_code == 413
    did = published["message"]["documentId"]
    timings = []
    for i in range(100):
        before = time.perf_counter()
        response = await live.recipient.post(
            "/v3/verifications",
            json={
                "request_id": f"req_performance_{i}",
                "document_id": did,
                "version": 1,
                "scope": "PROTECTED_FIELDS",
                "candidate": published["content"],
            },
        )
        timings.append((time.perf_counter() - before) * 1000)
        assert response.status_code == 200
        assert response.json()["verification_status"] == "VERIFIED"
    metrics = {
        "sample_count": len(timings),
        "p50_ms": statistics.median(timings),
        "p95_ms": sorted(timings)[int(len(timings) * 0.95) - 1],
        "path": "POST /v3/verifications; PROTECTED_FIELDS, version 1; unique request IDs",
        "scope": "real local HTTP/PostgreSQL; synthetic Registry, no model latency",
    }
    evidence = ROOT / "build/v5-c-performance.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics))


async def test_v5_rpc_outage_analysis_and_expiry_are_independent(wallet_live):
    live = wallet_live
    signing = await draft(live)
    await publish(live, signing)
    did = signing["message"]["documentId"]
    live.state["offline"] = True
    write_state(live.tmp / "chain.json", live.state)
    assert (await live.bank.get("/health/ready")).status_code == 503
    assert (await live.bank.get("/health/live")).status_code == 200
    checked = await live.recipient.post(
        "/v3/verifications",
        json={
            "request_id": "req_rpc_outage",
            "document_id": did,
            "scope": "PROTECTED_FIELDS",
            "candidate": signing["content"],
        },
    )
    assert checked.status_code == 200 and checked.json()["verification_status"] == "INCONCLUSIVE"
    body, analysis_id = await analyze(
        live,
        retain_report=True,
        retain_original=True,
        verification_session_id=checked.json()["session_id"],
    )
    result = await until(lambda: analysis_status(live, analysis_id, "COMPLETED"))
    assert result["report"]["risk_level"] == "CAUTION"
    assert result["report"]["verification"]["verification_status"] == "INCONCLUSIVE"
    async with live.database.session_factory() as db:
        row = await db.get(WalletAnalysisRow, analysis_id)
        raw = await db.get(WalletInputRow, body["input_ref"])
        row.report_expires_at = row.original_expires_at = raw.expires_at = int(time.time()) - 1
        await db.commit()
    for suffix in ("report", "original"):
        assert (await live.recipient.get(f"/v3/analyses/{analysis_id}/{suffix}")).status_code == 410
    async with live.database.session_factory() as db:
        assert (await db.get(WalletAnalysisRow, analysis_id)).report is not None
        assert (await db.get(WalletInputRow, body["input_ref"])).original is not None
    live.stop()
    live.state["offline"] = False
    write_state(live.tmp / "chain.json", live.state)
    live.start()
    await wait_http(live.url + "/health/ready")
    async with live.database.session_factory() as db:
        assert (await db.get(WalletAnalysisRow, analysis_id)).report is None
        assert (await db.get(WalletInputRow, body["input_ref"])).original is None
    assert (await live.bank.get(f"/v3/documents/{did}/verification-material")).status_code == 200


async def test_v5_postgres_retention_preserves_legacy_and_unresolved_audit(wallet_live):
    from types import SimpleNamespace

    from originproof_api.wallet_analyses import cleanup

    live = wallet_live
    stamp = int(time.time())
    old = datetime.fromtimestamp(stamp, UTC) - timedelta(days=31)
    async with live.database.session_factory() as db:
        for name, action, status, resolved in [
            ("expired", "wallet_publish", "CONFIRMED", stamp - 31 * 86400),
            ("pending", "wallet_publish", "UNKNOWN", None),
            ("legacy", "publish", "CONFIRMED", stamp - 31 * 86400),
            ("lookalike", "walletXpublish", "CONFIRMED", stamp - 31 * 86400),
        ]:
            db.add(
                OperationRow(
                    operation_id="op_retention_" + name,
                    account_id="acct_bank",
                    issuer_id=ISSUER,
                    action=action,
                    request_id="req_retention_" + name,
                    input_hash="0" * 64,
                    status=status,
                    input_body={},
                    target_id="target_retention_" + name,
                    recovery_reference={"resolved_at": resolved},
                    created_at=old,
                )
            )
            db.add(
                AuditEventRow(
                    event_id="evt_retention_" + name,
                    actor_account_id="acct_bank",
                    action=action,
                    target_id="target_retention_" + name,
                    after_status=status,
                    created_at=old,
                )
            )
        await db.commit()
    app = SimpleNamespace(
        state=SimpleNamespace(
            wallet_runtime=WalletRuntime(live.database, Settings(_env_file=None)),
            analysis_worker_error=None,
        )
    )
    await cleanup(app)
    async with live.database.session_factory() as db:
        assert await db.get(OperationRow, "op_retention_expired") is None
        assert await db.get(AuditEventRow, "evt_retention_expired") is None
        for name in ("pending", "legacy", "lookalike"):
            assert await db.get(OperationRow, "op_retention_" + name) is not None
            assert await db.get(AuditEventRow, "evt_retention_" + name) is not None
