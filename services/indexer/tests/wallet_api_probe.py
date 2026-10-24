"""Opt-in real PostgreSQL + ASGI handlers + Anvil; seeded onboarding is not a UI test."""

import asyncio
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
from infrastructure.blockchain.wallet_adapter import WalletRegistryReadAdapter
from infrastructure.blockchain.wallet_recovery import calldata
from originproof_api.accounts import password_hash
from originproof_api.database import AccountRow, Database, IssuerApplicationRow, OperationRow
from originproof_api.main import create_app
from originproof_api.settings import Settings
from originproof_api.wallet_database import WalletOnboardingRow
from originproof_core.canonicalization import canonical_json_bytes
from originproof_core.wallet_contract import GovernanceProposal, KeyProofMessage, SigningRequest
from originproof_core.wallet_signatures import identifier_hash, proposal_id, typed_data

ROOT = Path(__file__).resolve().parents[3]


@asynccontextmanager
async def disposable_database():
    name = "originproof_wallet_api_" + uuid4().hex
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    database = None
    try:
        subprocess.run(
            [
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
                f"127.0.0.1:{port}:5432",
                "-e",
                "POSTGRES_USER=originproof",
                "-e",
                "POSTGRES_PASSWORD=originproof",
                "-e",
                "POSTGRES_DB=originproof",
                "postgres:16.4-alpine",
            ],
            check=True,
            capture_output=True,
        )
        for _ in range(100):
            ready = subprocess.run(
                ["docker", "exec", name, "pg_isready", "-U", "originproof"],
                capture_output=True,
            )
            if ready.returncode == 0:
                break
            await asyncio.sleep(0.1)
        else:
            raise AssertionError("disposable PostgreSQL did not start")
        url = f"postgresql+asyncpg://originproof:originproof@127.0.0.1:{port}/originproof"
        env = os.environ | {
            "API_DATABASE_URL": url,
            "PYTHONPATH": ":".join(
                str(ROOT / p)
                for p in (
                    "apps/api/src",
                    "packages/python",
                    "services/indexer/src",
                    "services/analyzer/src",
                )
            ),
        }
        await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-m", "alembic", "-c", "apps/api/alembic.ini", "upgrade", "head"],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
        )
        database = Database(url)
        yield database
    finally:
        if database is not None:
            await database.dispose()
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


async def probe_wallet_api(reader, creation_proof, approvers, institution, abi):
    from originproof_core.wallet_contract import WalletDomain

    domain = WalletDomain(chain_id=str(reader.chain_id), verifying_contract=reader.address)
    issuer_name = "iss_origin_mock_bank"
    issuer, key = identifier_hash(issuer_name), identifier_hash("api-probe-key")
    metadata = {
        "issuer_id": issuer_name,
        "name": "Origin Mock Bank",
        "domain": "bank.example.invalid",
    }
    deadline = int(time.time()) + 3600

    async def signature(message):
        return await reader.rpc(
            "eth_signTypedData_v4",
            [institution, json.dumps(typed_data(domain, message))],
        )

    async def send(function, arguments, sender):
        return await reader.rpc(
            "eth_sendTransaction",
            [
                {
                    "from": sender,
                    "to": reader.address,
                    "gas": "0x800000",
                    "data": "0x" + calldata(reader, function, arguments).hex(),
                }
            ],
        )

    async def mined(tx_hash):
        for _ in range(100):
            receipt = await reader.rpc("eth_getTransactionReceipt", [tx_hash])
            if receipt is not None:
                assert receipt["status"] == "0x1"
                return
            await asyncio.sleep(0.05)
        raise AssertionError("disposable API transaction was not mined")

    proposal = GovernanceProposal(
        action=1,
        issuer_id=issuer,
        key_id=key,
        signer=institution,
        metadata_hash="0x" + hashlib.sha256(canonical_json_bytes(metadata)).hexdigest(),
        nonce="0",
        deadline=deadline,
    )
    proof = KeyProofMessage(
        application_id=identifier_hash("app_api_probe"),
        issuer_id=issuer,
        signer=institution,
        challenge_nonce=identifier_hash("api-probe-challenge"),
        deadline=deadline,
    )
    proposal_args = proposal.model_dump(by_alias=True) | {"nonce": 0}
    registration_tx = await send(
        "propose",
        {
            "proposal": proposal_args,
            "proof": proof.model_dump(by_alias=True),
            "signature": await signature(proof),
        },
        approvers[0],
    )
    await mined(registration_tx)
    pid = proposal_id(domain, proposal)
    for actor in approvers[:2]:
        await mined(await send("approve", {"proposalId": pid}, actor))

    adapter = await WalletRegistryReadAdapter.from_deployment(
        reader.client,
        reader.url,
        creation_proof=creation_proof,
        chain_id=reader.chain_id,
        address=reader.address,
        deployment_block=reader.deployment_block,
        deployment_hash=reader.deployment_hash,
        runtime_code_hash=reader.runtime_code_hash,
        abi=abi,
    )
    async with disposable_database() as database:
        hashed = await asyncio.to_thread(password_hash, "synthetic-api-probe-password")
        async with database.session_factory() as db:
            for account, role, owner in (
                ("issuer", "issuer", issuer_name),
                ("internal", "issuer", issuer_name),
                ("other", "issuer", "iss_origin_mock_office"),
                ("recipient", "recipient", None),
                ("operator", "operator", None),
            ):
                db.add(
                    AccountRow(
                        account_id="acct_api_" + account,
                        username=account,
                        password_hash=hashed,
                        role=role,
                        issuer_id=owner,
                    )
                )
            await db.flush()
            db.add(
                IssuerApplicationRow(
                    application_id="app_api_probe",
                    issuer_id=issuer_name,
                    applicant_account_id="acct_api_issuer",
                    issuer_name=metadata["name"],
                    status="PENDING_REVIEW",
                )
            )
            await db.flush()
            db.add(
                WalletOnboardingRow(
                    application_id="app_api_probe",
                    email="staff@bank.example.invalid",
                    email_verified=True,
                    internally_approved=True,
                    approved_by="acct_api_internal",
                    metadata_value=metadata,
                )
            )
            await db.commit()
        settings = Settings(
            _env_file=None,
            wallet_registry_address=reader.address,
            blockchain_chain_id=reader.chain_id,
            wallet_operator_addresses={"acct_api_operator": approvers[0]},
        )
        unconfigured_app = create_app(database=database, settings=settings)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=unconfigured_app),
            base_url="http://test",
        ) as unconfigured_api:
            unavailable = await unconfigured_api.get(
                "/v3/documents/" + identifier_hash("unregistered-api-probe"),
            )
            assert unavailable.status_code == 503, unavailable.text
        app = create_app(database=database, settings=settings, wallet_chain=adapter)

        async def login(api, username):
            result = await api.post(
                "/v1/auth/login",
                json={
                    "username": username,
                    "password": "synthetic-api-probe-password",
                },
            )
            assert result.status_code == 200, result.text
            api.headers["X-CSRF-Token"] = result.json()["csrf_token"]

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as api:
            absent = await api.get("/v3/documents/" + identifier_hash("unregistered-api-probe"))
            assert absent.status_code == 404, absent.text
            body = {
                "request_id": "req_api_draft",
                "doc_key": identifier_hash("api-probe-doc"),
                "expected_version": 1,
                "expires_at": int(time.time()) + 86400,
                "content": {
                    "notice_type": "OFFICIAL_DOCUMENT",
                    "institution_code": "ORIGIN_MOCK_BANK",
                    "document_type": "NOTICE",
                    "document_number": "API-001",
                    "title": "Synthetic",
                    "summary": "Disposable PostgreSQL and Anvil",
                    "official_url": None,
                },
            }
            assert (await api.post("/v3/document-drafts", json=body)).status_code == 401
            await login(api, "recipient")
            assert (await api.post("/v3/document-drafts", json=body)).status_code == 403
            await login(api, "operator")
            assert (await api.get(f"/v3/proposals/{pid}")).status_code == 404
            settings.wallet_operator_addresses["acct_api_operator"] = institution
            assert (await api.get(f"/v3/proposals/{pid}")).status_code == 403
            settings.wallet_operator_addresses["acct_api_operator"] = approvers[0]
            await login(api, "issuer")
            csrf = api.headers.pop("X-CSRF-Token")
            assert (await api.post("/v3/document-drafts", json=body)).status_code == 403
            api.headers["X-CSRF-Token"] = csrf
            draft = await api.post("/v3/document-drafts", json=body)
            assert draft.status_code == 201, draft.text
            signing = SigningRequest.model_validate(draft.json())
            signed = await signature(signing.message)
            submission = {
                "request_id": "req_api_publish",
                "signing_request_id": signing.signing_request_id,
                "signature": signed,
            }
            pending = await api.post("/v3/publications", json=submission)
            assert pending.status_code == 202, pending.text
            assert pending.json()["status"] == "PENDING_SUBMISSION"
            operation_id = pending.json()["operation_id"]
            reconcile = f"/v3/operations/{operation_id}/reconcile"
            unconfigured = await api.post(reconcile)
            assert unconfigured.status_code == 503, unconfigured.text
            await login(api, "other")
            assert (await api.get(f"/v3/operations/{operation_id}")).status_code == 404
            await login(api, "issuer")
            mismatch = await api.post(
                f"/v3/signing-requests/{signing.signing_request_id}/transactions",
                json={
                    "request_id": "req_api_wrong_tx",
                    "signing_request_id": signing.signing_request_id,
                    "tx_hash": registration_tx,
                },
            )
            assert mismatch.status_code == 422, mismatch.text
            assert mismatch.json()["detail"] == "DIRECT_TX_MISMATCH"
            await reader.rpc("evm_setAutomine", [False])
            try:
                tx_hash = await send(
                    "publish",
                    {
                        "message": signing.message.model_dump(by_alias=True)
                        | {"nonce": int(signing.message.nonce)},
                        "signature": signed,
                    },
                    institution,
                )
                response = await api.post(
                    f"/v3/signing-requests/{signing.signing_request_id}/transactions",
                    json={
                        "request_id": "req_api_direct",
                        "signing_request_id": signing.signing_request_id,
                        "tx_hash": tx_hash,
                    },
                )
                assert response.status_code == 202, response.text
                assert response.json()["status"] == "UNKNOWN"
            finally:
                await reader.rpc("evm_mine", [])
                await reader.rpc("evm_setAutomine", [True])
            await mined(tx_hash)

        # Recreate API and its DB pool; no overrides, synthetic chain port or resent transaction.
        await database.dispose()
        restarted_database = Database(
            str(database.engine.url.render_as_string(hide_password=False))
        )
        restarted = create_app(database=restarted_database, settings=settings, wallet_chain=adapter)
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=restarted),
                base_url="http://test",
            ) as api:
                await login(api, "issuer")
                restored = await api.get(f"/v3/operations/{operation_id}")
                assert restored.json()["status"] == "UNKNOWN"
                result = await api.post(reconcile)
                assert result.status_code == 202, result.text
                assert result.json()["status"] == "CONFIRMED"
                assert result.json()["tx_hash"] == tx_hash
                again = await api.post(reconcile)
                assert again.json() == result.json()
                did = signing.message.document_id
                document = await api.get(f"/v3/documents/{did}")
                assert document.status_code == 200 and document.json()["state"] == "ACTIVE"
                material = await api.get(f"/v3/documents/{did}/verification-material")
                assert material.status_code == 200, material.text
                assert material.json()["signature"] == signed
                verified = await api.post(
                    "/v3/verifications",
                    json={
                        "request_id": "req_api_verify",
                        "document_id": did,
                        "scope": "PROTECTED_FIELDS",
                        "candidate": body["content"],
                    },
                )
                assert verified.status_code == 200, verified.text
                assert verified.json()["verification_status"] == "VERIFIED", verified.text
                async with restarted_database.session_factory() as db:
                    saved = await db.get(OperationRow, operation_id)
                    assert saved.tx_hash == tx_hash and saved.status == "CONFIRMED"
                    assert saved.recovery_reference["lookup_tx_hash"] == tx_hash
        finally:
            await restarted_database.dispose()
    return {
        "scope": "Anvil + migrated disposable PostgreSQL + ASGI and real login/CSRF",
        "publication_tx": tx_hash,
        "operation": "UNKNOWN to CONFIRMED after API/pool recreation",
        "limitations": [
            "seeded onboarding",
            "no browser/network API process/lifespan",
            "hashless search remains 503; relayer remains disabled",
        ],
    }
