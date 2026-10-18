"""Real SQLAlchemy storage/HTTP and signed inputs; Registry evidence is synthetic."""

import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from eth_keys import keys
from httpx import ASGITransport, AsyncClient
from originproof_api.accounts import current_session
from originproof_api.database import AccountRow, Base, IssuerApplicationRow
from originproof_api.main import create_app
from originproof_api.settings import Settings
from originproof_api.wallet_database import WalletOnboardingRow
from originproof_api.wallet_documents import optional_session
from originproof_core.wallet_contract import SigningRequest, WalletDomain
from originproof_core.wallet_ports import WalletProposal, WalletTransaction
from originproof_core.wallet_signatures import identifier_hash, wallet_digest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from test_w2_chain_management import AsyncSession

ISSUER = "iss_origin_mock_bank"
ISSUER_HASH = identifier_hash(ISSUER)
DOMAIN = WalletDomain(chainId="31337", verifyingContract="0x" + "12" * 20)
KEY = keys.PrivateKey((1).to_bytes(32, "big"))
SIGNER = KEY.public_key.to_checksum_address().lower()
APPROVERS = ["0x" + x * 40 for x in "234"]
BLOCK = {
    "chain_id": "31337",
    "verifying_contract": DOMAIN.verifying_contract,
    "block_number": "10",
    "block_hash": "0x" + "ab" * 32,
}


def sign(signing):
    signing = SigningRequest.model_validate(signing) if isinstance(signing, dict) else signing
    raw = KEY.sign_msg_hash(
        bytes.fromhex(wallet_digest(signing.domain, signing.message)[2:])
    ).to_bytes()
    return "0x" + (raw[:64] + bytes([raw[64] + 27])).hex()


class Chain:
    def __init__(self):
        self.issuers, self.keys, self.documents, self.proposals, self.transactions = (
            {},
            {},
            {},
            {},
            {},
        )
        self.sends = []

    async def is_approver(self, address):
        return address in APPROVERS

    async def issuer(self, issuer_id):
        return self.issuers.get(issuer_id)

    async def key(self, key_id):
        return self.keys.get(key_id)

    async def proposal(self, proposal_id):
        return self.proposals.get(proposal_id)

    async def transaction(self, tx_hash):
        return self.transactions.get(tx_hash)

    async def document(self, document_id, version):
        candidates = [v for (did, _), v in self.documents.items() if did == document_id]
        if version is None:
            return max(candidates, key=lambda v: v.document.version, default=None)
        return self.documents.get((document_id, version))

    async def submit(self, request, signature):
        self.sends.append((request, signature))
        return None

    async def find_transaction(self, intent):
        return next(
            (
                tx
                for tx in self.transactions.values()
                if tx.action == intent["action"] and tx.arguments == intent["arguments"]
            ),
            None,
        )


@pytest.fixture
async def wallet():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    accounts = {
        "issuer": AccountRow(account_id="acct_i", username="i", role="issuer", issuer_id=ISSUER),
        "internal": AccountRow(
            account_id="acct_internal", username="in", role="issuer", issuer_id=ISSUER
        ),
        "operator": AccountRow(account_id="acct_o", username="o", role="operator"),
        "operator2": AccountRow(account_id="acct_o2", username="o2", role="operator"),
        "other": AccountRow(
            account_id="acct_x", username="x", role="issuer", issuer_id="iss_other"
        ),
        "recipient": AccountRow(account_id="acct_r", username="r", role="recipient"),
    }
    with Session(engine, expire_on_commit=False) as db:
        for row in accounts.values():
            row.password_hash = "unused"
            db.add(row)
        db.add(
            IssuerApplicationRow(
                application_id="app_test",
                issuer_id=ISSUER,
                applicant_account_id="acct_i",
                issuer_name="Origin Mock Bank",
                status="PENDING_REVIEW",
            )
        )
        db.commit()
    chain = Chain()
    database = SimpleNamespace(session_factory=lambda: AsyncSession(engine))
    settings = Settings(
        wallet_registry_address=DOMAIN.verifying_contract,
        wallet_operator_addresses={"acct_o": APPROVERS[0], "acct_o2": APPROVERS[1]},
        wallet_internal_approvers={ISSUER: "acct_internal"},
        wallet_demo_email_enabled=True,
        wallet_email_secret="synthetic-wallet-email-secret-for-tests-only",
    )
    app = create_app(database=database, settings=settings, wallet_chain=chain)
    who = {"name": "issuer"}

    async def identity():
        return accounts[who["name"]], SimpleNamespace(csrf_token="csrf")

    app.dependency_overrides[current_session] = identity
    app.dependency_overrides[optional_session] = identity
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers={"X-CSRF-Token": "csrf"}
    ) as client:
        yield SimpleNamespace(
            client=client, engine=engine, chain=chain, app=app, who=who, accounts=accounts
        )
    engine.dispose()


async def onboarding(w):
    c = w.client
    issued = await c.post(
        "/v3/issuer-applications/app_test/email-codes", json={"email": "staff@bank.example.invalid"}
    )
    assert issued.status_code == 201, issued.text
    inbox = await c.get("/v3/issuer-applications/app_test/demo-inbox")
    verified = await c.post(
        "/v3/issuer-applications/app_test/email-verifications", json={"code": inbox.json()["code"]}
    )
    assert verified.status_code == 200, verified.text
    w.who["name"] = "internal"
    approved = await c.post(
        "/v3/issuer-applications/app_test/internal-approvals",
        json={"decision": "APPROVE", "reason": "synthetic review"},
    )
    assert approved.status_code == 200, approved.text
    w.who["name"] = "issuer"
    return approved.json()


async def proved_key(w):
    checks = await onboarding(w)
    body = {"request_id": "req_key", "application_id": "app_test", "signer": SIGNER}
    challenge = await w.client.post("/v3/key-challenges", json=body)
    assert challenge.status_code == 201, challenge.text
    data = challenge.json()
    submission = {
        "request_id": "req_proof",
        "signing_request_id": data["signing_request_id"],
        "signature": sign(data),
    }
    response = await w.client.post("/v3/key-proofs", json=submission)
    assert response.status_code == 200, response.text
    return checks, data, submission


async def prepared_proposal(w):
    checks, signing, _ = await proved_key(w)
    w.who["name"] = "operator"
    body = {
        "request_id": "req_proposal",
        "key_proof_request_id": signing["signing_request_id"],
        "proposal": {
            "action": 1,
            "issuerId": ISSUER_HASH,
            "keyId": identifier_hash("key_test"),
            "signer": SIGNER,
            "metadataHash": checks["metadata_hash"],
            "nonce": "0",
            "deadline": signing["message"]["deadline"],
        },
    }
    response = await w.client.post("/v3/proposals", json=body)
    assert response.status_code == 201, response.text
    return response.json(), body


async def test_onboarding_requires_roster_email_independent_internal_approval(wallet):
    w = wallet
    response = await w.client.post(
        "/v3/key-challenges",
        json={"request_id": "req_early", "application_id": "app_test", "signer": SIGNER},
    )
    assert response.status_code == 409
    bad = await w.client.post(
        "/v3/issuer-applications/app_test/email-codes", json={"email": "staff@attacker.invalid"}
    )
    assert bad.status_code == 422
    await onboarding(w)
    replay = await w.client.post(
        "/v3/issuer-applications/app_test/email-verifications", json={"code": "000000"}
    )
    assert replay.status_code == 410
    denied = await w.client.post(
        "/v3/issuer-applications/app_test/internal-approvals",
        json={"decision": "APPROVE", "reason": "self"},
    )
    assert denied.status_code == 403
    w.who["name"] = "other"
    assert (await w.client.get("/v3/issuer-applications/app_test/demo-inbox")).status_code == 404


async def test_email_failure_and_reissue_limits_persist(wallet, monkeypatch):
    monkeypatch.setattr("originproof_api.wallet_onboarding.secrets.randbelow", lambda _: 123456)
    c = wallet.client
    path = "/v3/issuer-applications/app_test/"
    assert (
        await c.post(path + "email-codes", json={"email": "staff@bank.example.invalid"})
    ).status_code == 201
    assert (
        await c.post(path + "email-codes", json={"email": "staff@bank.example.invalid"})
    ).status_code == 429
    for _ in range(5):
        assert (
            await c.post(path + "email-verifications", json={"code": "000000"})
        ).status_code == 422
    assert (await c.post(path + "email-verifications", json={"code": "123456"})).status_code == 429
    with Session(wallet.engine) as db:
        row = db.get(WalletOnboardingRow, "app_test")
        assert row.code_hash is None and row.demo_code is None


async def test_email_verifier_requires_server_secret_and_clears_consumed_code(wallet, monkeypatch):
    from pydantic import SecretStr

    monkeypatch.setattr("originproof_api.wallet_onboarding.secrets.randbelow", lambda _: 123456)
    settings = wallet.app.state.settings
    secret = settings.wallet_email_secret
    path = "/v3/issuer-applications/app_test/"
    settings.wallet_email_secret = None
    missing = await wallet.client.post(
        path + "email-codes", json={"email": "staff@bank.example.invalid"}
    )
    assert missing.status_code == 503
    settings.wallet_email_secret = secret
    issued = await wallet.client.post(
        path + "email-codes", json={"email": "staff@bank.example.invalid"}
    )
    assert issued.status_code == 201
    assert "wallet_email_secret" not in settings.model_dump()
    assert secret.get_secret_value() not in repr(settings) + issued.text
    with Session(wallet.engine) as db:
        stored = db.get(WalletOnboardingRow, "app_test").code_hash
        _, salt, digest = stored.split(":")
        assert digest != hashlib.sha256((salt + "123456").encode()).hexdigest()
    settings.wallet_email_secret = SecretStr("rotated-synthetic-server-secret-for-test")
    rejected = await wallet.client.post(path + "email-verifications", json={"code": "123456"})
    assert rejected.status_code == 422 and rejected.json()["detail"] == "EMAIL_CODE_INVALID"
    settings.wallet_email_secret = secret
    accepted = await wallet.client.post(path + "email-verifications", json={"code": "123456"})
    assert accepted.status_code == 200
    with Session(wallet.engine) as db:
        row = db.get(WalletOnboardingRow, "app_test")
        assert row.email_verified and row.code_hash is None and row.demo_code is None


@pytest.mark.parametrize("access", ["demo-inbox", "email-verifications", "maintenance"])
async def test_email_expiry_erases_verifier_and_plaintext(wallet, monkeypatch, access):
    from originproof_api.wallet_onboarding import expire_codes

    stamp = int(time.time())
    monkeypatch.setattr("originproof_api.wallet_onboarding.now", lambda: stamp)
    path = "/v3/issuer-applications/app_test/"
    assert (
        await wallet.client.post(path + "email-codes", json={"email": "staff@bank.example.invalid"})
    ).status_code == 201
    stamp += 299
    still_valid = await wallet.client.get(path + "demo-inbox")
    assert still_valid.status_code == 200 and still_valid.json()["code"] is not None
    stamp += 1
    if access == "demo-inbox":
        response = await wallet.client.get(path + access)
        assert response.status_code == 200 and response.json()["code"] is None
    elif access == "email-verifications":
        response = await wallet.client.post(path + access, json={"code": "123456"})
        assert response.status_code == 410
    else:
        await expire_codes(wallet.app)
    with Session(wallet.engine) as db:
        row = db.get(WalletOnboardingRow, "app_test")
        assert row.code_hash is None and row.demo_code is None


async def test_legacy_unkeyed_email_verifier_is_invalidated(wallet):
    path = "/v3/issuer-applications/app_test/"
    await wallet.client.post(path + "email-codes", json={"email": "staff@bank.example.invalid"})
    with Session(wallet.engine) as db:
        row = db.get(WalletOnboardingRow, "app_test")
        row.code_hash = "salt:" + hashlib.sha256(b"salt123456").hexdigest()
        db.commit()
    response = await wallet.client.post(path + "email-verifications", json={"code": "123456"})
    assert response.status_code == 410
    with Session(wallet.engine) as db:
        row = db.get(WalletOnboardingRow, "app_test")
        assert row.code_hash is None and row.demo_code is None and not row.email_verified


async def test_reissuing_email_code_does_not_reset_cumulative_failure_budget(wallet, monkeypatch):
    stamp = int(time.time())
    monkeypatch.setattr("originproof_api.wallet_onboarding.now", lambda: stamp)
    monkeypatch.setattr("originproof_api.wallet_onboarding.secrets.randbelow", lambda _: 123456)
    path = "/v3/issuer-applications/app_test/"
    for _ in range(2):
        issued = await wallet.client.post(
            path + "email-codes", json={"email": "staff@bank.example.invalid"}
        )
        assert issued.status_code == 201
        for _ in range(5):
            invalid = await wallet.client.post(
                path + "email-verifications", json={"code": "000000"}
            )
            assert invalid.status_code == 422
        stamp += 60
    blocked = await wallet.client.post(
        path + "email-codes", json={"email": "staff@bank.example.invalid"}
    )
    assert blocked.status_code == 429 and blocked.json()["detail"] == "EMAIL_ATTEMPT_LIMIT"


async def test_email_startup_cleanup_erases_expired_codes_without_new_requests(wallet, monkeypatch):
    stamp = int(time.time())
    monkeypatch.setattr("originproof_api.wallet_onboarding.now", lambda: stamp)

    async def dispose():
        pass

    monkeypatch.setattr(wallet.app.state.database, "dispose", dispose, raising=False)
    issued = await wallet.client.post(
        "/v3/issuer-applications/app_test/email-codes",
        json={"email": "staff@bank.example.invalid"},
    )
    assert issued.status_code == 201
    stamp += 300
    async with wallet.app.router.lifespan_context(wallet.app):
        with Session(wallet.engine) as db:
            row = db.get(WalletOnboardingRow, "app_test")
            assert row.code_hash is None and row.demo_code is None


@pytest.mark.skipif(
    shutil.which("cast") is None, reason="Foundry cast is required for ABI encoding"
)
async def test_reactivation_uses_abi_encodable_zero_proof_and_empty_signature(wallet):
    from originproof_api.database import OperationRow
    from originproof_core.wallet_ports import WalletIssuer, WalletKey

    key_id = identifier_hash("key_reactivate")
    metadata = "0x" + "cd" * 32
    wallet.chain.issuers[ISSUER_HASH] = WalletIssuer(
        **BLOCK,
        issuer_id=ISSUER_HASH,
        state="SUSPENDED",
        key_id=key_id,
        signer=SIGNER,
        metadata_hash=metadata,
        next_nonce="0",
        governance_nonce="0",
    )
    wallet.chain.keys[key_id] = WalletKey(
        **BLOCK, key_id=key_id, issuer_id=ISSUER_HASH, signer=SIGNER, registered_block="1"
    )
    wallet.who["name"] = "operator"
    response = await wallet.client.post(
        "/v3/proposals",
        json={
            "request_id": "req_reactivate",
            "key_proof_request_id": None,
            "proposal": {
                "action": 3,
                "issuerId": ISSUER_HASH,
                "keyId": key_id,
                "signer": SIGNER,
                "metadataHash": metadata,
                "nonce": "0",
                "deadline": int(time.time()) + 300,
            },
        },
    )
    assert response.status_code == 201, response.text
    pid = response.json()["proposal_id"]
    accepted = await wallet.client.post(
        f"/v3/proposals/{pid}/transactions",
        json={"request_id": "req_reactivate_tx", "tx_hash": "0x" + "56" * 32},
    )
    assert accepted.status_code == 202, accepted.text
    with Session(wallet.engine) as db:
        args = (
            db.query(OperationRow)
            .filter_by(request_id="req_reactivate_tx")
            .one()
            .input_body["arguments"]
        )
    abi = json.loads(Path("packages/contracts/abi/IOriginProofWalletRegistry.json").read_text())
    function = next(f for f in abi if f.get("name") == "propose")

    def abi_type(item):
        return (
            "(" + ",".join(abi_type(c) for c in item["components"]) + ")"
            if item["type"] == "tuple"
            else item["type"]
        )

    def abi_value(item, value):
        return (
            "(" + ",".join(abi_value(c, value[c["name"]]) for c in item["components"]) + ")"
            if item["type"] == "tuple"
            else str(value)
        )

    signature = "propose(" + ",".join(abi_type(i) for i in function["inputs"]) + ")"
    values = [abi_value(i, args[i["name"]]) for i in function["inputs"]]
    encoded = subprocess.check_output(["cast", "calldata", signature, *values], text=True).strip()
    assert len(bytes.fromhex(encoded[2:])) == 4 + 15 * 32
    assert args["signature"] == "0x" and all(
        value == 0 or int(value, 16) == 0 for value in args["proof"].values()
    )


async def test_key_proof_signature_idempotency_replay_and_body_conflict(wallet):
    _, signing, submission = await proved_key(wallet)
    retry = await wallet.client.post("/v3/key-proofs", json=submission)
    assert retry.status_code == 200
    assert (
        await wallet.client.post("/v3/key-proofs", json={**submission, "request_id": "req_replay"})
    ).status_code == 409
    changed = {"request_id": "req_key", "application_id": "app_test", "signer": APPROVERS[0]}
    assert (await wallet.client.post("/v3/key-challenges", json=changed)).status_code == 409
    assert SigningRequest.model_validate(signing).message.signer == SIGNER


async def test_proposal_preparation_does_not_activate_or_count_approval(wallet):
    proposal, body = await prepared_proposal(wallet)
    assert proposal["status"] == "PREPARED" and proposal["approvals"] == []
    assert wallet.chain.issuers == {} and wallet.chain.sends == []
    retry = await wallet.client.post("/v3/proposals", json=body)
    assert retry.json()["proposal_id"] == proposal["proposal_id"]
    changed = {**body, "request_id": "req_reused_proof"}
    assert (await wallet.client.post("/v3/proposals", json=changed)).status_code == 409


async def test_governance_tx_requires_decoded_call_and_two_chain_approvers(wallet):
    data, _ = await prepared_proposal(wallet)
    pid, tx_hash = data["proposal_id"], "0x" + "45" * 32
    from originproof_core.wallet_contract import ProposalView

    chain_view = ProposalView.model_validate(data).model_copy(update={"status": "PENDING"})
    wallet.chain.proposals[pid] = WalletProposal(**BLOCK, proposal=chain_view)
    wallet.chain.transactions[tx_hash] = WalletTransaction(
        **BLOCK,
        tx_hash=tx_hash,
        sender=APPROVERS[0],
        action="Propose",
        status="CONFIRMED",
        arguments={
            "proposal": body_proposal(data),
            "proof": data["key_proof"],
            "signature": data["key_proof_signature"],
        },
    )
    accepted = await wallet.client.post(
        f"/v3/proposals/{pid}/transactions", json={"request_id": "req_tx", "tx_hash": tx_hash}
    )
    assert accepted.status_code == 202, accepted.text
    assert accepted.json()["status"] == "CONFIRMED"
    shown = await wallet.client.get(f"/v3/proposals/{pid}")
    assert shown.json()["status"] == "PENDING" and shown.json()["approvals"] == []
    wrong = wallet.chain.transactions[tx_hash].model_copy(update={"arguments": {}})
    wallet.chain.transactions[tx_hash] = wrong
    denied = await wallet.client.post(
        f"/v3/proposals/{pid}/transactions", json={"request_id": "req_wrong_tx", "tx_hash": tx_hash}
    )
    assert denied.status_code == 422


def body_proposal(data):
    from originproof_core.wallet_contract import GovernanceProposal

    return GovernanceProposal.model_validate(data["proposal"]).model_dump(by_alias=True)


async def test_v3_security_and_unavailable_adapter_do_not_claim_success(wallet):
    wallet.who["name"] = "operator"
    wallet.app.state.wallet_runtime.chain = None
    assert (await wallet.client.get("/v3/proposals/" + "0x" + "11" * 32)).status_code == 503
    blocked = await wallet.client.post(
        "/v3/key-challenges", json={}, headers={"Origin": "https://attacker.invalid"}
    )
    assert blocked.status_code == 403 and blocked.headers["Cache-Control"] == "no-store"
    wallet.who["name"] = "issuer"
    malformed = await wallet.client.post("/v3/key-challenges", json={"secret": "DO_NOT_ECHO"})
    assert malformed.status_code == 422 and "DO_NOT_ECHO" not in malformed.text


async def activated(w):
    from originproof_core.wallet_ports import WalletIssuer, WalletKey

    checks = await onboarding(w)
    kid = identifier_hash("key_active")
    w.chain.issuers[ISSUER_HASH] = WalletIssuer(
        **BLOCK,
        issuer_id=ISSUER_HASH,
        state="ACTIVE",
        key_id=kid,
        signer=SIGNER,
        metadata_hash=checks["metadata_hash"],
        next_nonce="0",
        governance_nonce="1",
    )
    w.chain.keys[kid] = WalletKey(
        **BLOCK, key_id=kid, issuer_id=ISSUER_HASH, signer=SIGNER, registered_block="2"
    )


def payment_content():
    import time

    return {
        "notice_type": "PAYMENT_REQUEST",
        "amount_minor": 154000,
        "currency": "KRW",
        "payee_bank_name": "합성 은행",
        "payee_account_number": "001234567890",
        "payee_account_holder": "합성 기관",
        "payment_purpose": "합성 납부 안내",
        "due_at": int(time.time()) + 3600,
        "official_url": "https://bank.example.invalid/pay",
    }


async def draft(w, *, request_id="req_draft", version=1, content=None):
    import time

    response = await w.client.post(
        "/v3/document-drafts",
        json={
            "request_id": request_id,
            "doc_key": identifier_hash("public_notice"),
            "expected_version": version,
            "expires_at": int(time.time()) + 86400,
            "content": content or payment_content(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def confirmed_publication(w, signing, *, req="req_publish", tx_byte="67"):
    from originproof_core.wallet_contract import DocumentView
    from originproof_core.wallet_ports import WalletDocument

    submitted = await w.client.post(
        "/v3/publications",
        json={
            "request_id": req,
            "signing_request_id": signing["signing_request_id"],
            "signature": sign(signing),
        },
    )
    assert submitted.status_code == 202, submitted.text
    assert submitted.json()["status"] in ("PENDING_SUBMISSION", "UNKNOWN")
    message = SigningRequest.model_validate(signing).message
    fields = {
        k: getattr(message, k)
        for k in (
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
    doc = DocumentView(
        **fields,
        latest_version=message.version,
        state="ACTIVE",
        warnings=[],
        original_available=False,
    )
    for identity, prior in list(w.chain.documents.items()):
        if identity[0] == message.document_id:
            w.chain.documents[identity] = prior.model_copy(
                update={
                    "document": prior.document.model_copy(
                        update={
                            "state": "SUPERSEDED",
                            "latest_version": message.version,
                        }
                    )
                }
            )
    w.chain.documents[(message.document_id, message.version)] = WalletDocument(
        **BLOCK,
        document=doc,
        published_at=message.issued_at,
        published_block="10",
    )
    w.chain.issuers[ISSUER_HASH] = w.chain.issuers[ISSUER_HASH].model_copy(
        update={"next_nonce": str(int(message.nonce) + 1)}
    )
    tx_hash = "0x" + tx_byte * 32
    w.chain.transactions[tx_hash] = WalletTransaction(
        **BLOCK,
        tx_hash=tx_hash,
        sender=APPROVERS[0],
        action="Publish",
        status="CONFIRMED",
        arguments={"message": message.model_dump(by_alias=True), "signature": sign(signing)},
    )
    confirmed = await w.client.post(
        f"/v3/signing-requests/{signing['signing_request_id']}/transactions",
        json={
            "request_id": "req_direct_" + req,
            "signing_request_id": signing["signing_request_id"],
            "tx_hash": tx_hash,
        },
    )
    assert confirmed.status_code == 202, confirmed.text
    assert confirmed.json()["status"] == "CONFIRMED"
    return doc, confirmed.json()


@pytest.mark.parametrize(
    "change,expected",
    [
        ({}, "CONFIRMED"),
        ({"state": "SUPERSEDED"}, "UNKNOWN"),
        ({"state": "ACTIVE"}, "UNKNOWN"),
        ({"state": "EXPIRED"}, "UNKNOWN"),
        ({"issuer_id": "0x" + "cd" * 32}, "UNKNOWN"),
        ({"doc_key": "0x" + "cd" * 32}, "UNKNOWN"),
        ({"document_id": "0x" + "cd" * 32}, "UNKNOWN"),
        ({"version": 2, "latest_version": 2}, "UNKNOWN"),
    ],
)
async def test_revoke_confirmation_requires_exact_revoked_document(wallet, change, expected):
    from originproof_api.wallet_database import WalletSigningRow
    from originproof_api.wallet_governance import accept_transaction
    from originproof_core.wallet_contract import RevokeDraftRequest, RevokeMessage, SignedSubmission

    await activated(wallet)
    original = await draft(wallet)
    doc, _ = await confirmed_publication(wallet, original)
    service = wallet.app.state.wallet_runtime
    message = RevokeMessage(
        issuerId=doc.issuer_id,
        docKey=doc.doc_key,
        documentId=doc.document_id,
        version=doc.version,
        keyId=doc.key_id,
        nonce="1",
        deadline=int(time.time()) + 300,
    )
    signing = SigningRequest(
        signing_request_id="wsr_review_revoke",
        primary_type="Revoke",
        domain=DOMAIN,
        message=message,
        expected_signer=SIGNER,
    )
    signature = sign(signing)
    body = SignedSubmission(
        request_id="req_review_revoke",
        signing_request_id=signing.signing_request_id,
        signature=signature,
    )
    intent = {
        "action": "Revoke",
        "signing_request_id": signing.signing_request_id,
        "document_id": doc.document_id,
        "version": doc.version,
        "arguments": {"message": message.model_dump(by_alias=True), "signature": signature},
    }
    tx_hash = "0x" + "ef" * 32
    wallet.chain.transactions[tx_hash] = WalletTransaction(
        **BLOCK,
        tx_hash=tx_hash,
        sender=APPROVERS[0],
        action="Revoke",
        status="CONFIRMED",
        arguments=intent["arguments"],
    )
    position = wallet.chain.documents[(doc.document_id, doc.version)]
    wallet.chain.documents[(doc.document_id, doc.version)] = position.model_copy(
        update={"document": doc.model_copy(update={"state": "REVOKED"} | change)}
    )
    async with service.database.session_factory() as db:
        await service.save_signing(
            db,
            wallet.accounts["issuer"],
            "Revoke",
            RevokeDraftRequest(
                request_id="req_review_revoke_draft",
                document_id=doc.document_id,
                version=doc.version,
            ),
            signing,
        )
        saved = await db.get(WalletSigningRow, signing.signing_request_id)
        saved.signature = signature
        row = service.operation(
            db, wallet.accounts["issuer"], "wallet_revoke", body, doc.document_id, intent
        )
        await service.commit(db)
        result = await accept_transaction(service, db, row, tx_hash)
        assert result.status == expected
    assert wallet.chain.sends == []


async def test_unsubmitted_expired_operation_reconciles_and_releases_nonce(wallet, monkeypatch):
    await activated(wallet)
    signing = await draft(wallet)
    body = {
        "request_id": "req_expiring",
        "signing_request_id": signing["signing_request_id"],
        "signature": sign(signing),
    }
    pending = await wallet.client.post("/v3/publications", json=body)
    assert pending.status_code == 202 and pending.json()["next_action"] == "RECONCILE"
    monkeypatch.setattr(
        "originproof_api.wallet_documents.now", lambda: signing["message"]["deadline"]
    )
    result = await wallet.client.post(f"/v3/operations/{pending.json()['operation_id']}/reconcile")
    assert result.status_code == 202 and result.json()["status"] == "FAILED"
    assert result.json()["next_action"] == "RESIGN" and wallet.chain.sends == []
    fresh = await draft(wallet, request_id="req_fresh_after_expiry")
    accepted = await wallet.client.post(
        "/v3/publications",
        json={
            "request_id": "req_after_expiry",
            "signing_request_id": fresh["signing_request_id"],
            "signature": sign(fresh),
        },
    )
    assert accepted.status_code == 202, accepted.text


async def test_publication_original_signature_and_operation_are_durable_without_server_key(wallet):
    import base64

    from originproof_api.wallet_database import WalletDocumentRow, WalletSigningRow
    from originproof_core.wallet_signatures import wallet_signer

    await activated(wallet)
    signing = await draft(wallet)
    doc, op = await confirmed_publication(wallet, signing)
    with Session(wallet.engine) as db:
        saved = db.get(WalletSigningRow, signing["signing_request_id"])
        row = db.get(WalletDocumentRow, ("31337", DOMAIN.verifying_contract, doc.document_id, 1))
        assert row.original == base64.b64decode(signing["original_base64"])
        assert saved.signature == row.signature == sign(signing)
    assert wallet.chain.sends == []
    viewed = await wallet.client.get(f"/v3/documents/{doc.document_id}")
    assert viewed.json()["version"] == 1 and viewed.json()["original_available"]
    material = await wallet.client.get(f"/v3/documents/{doc.document_id}/verification-material")
    assert material.status_code == 200, material.text
    payload = SigningRequest.model_validate(material.json()["signing_request"])
    assert wallet_signer(payload.domain, payload.message, material.json()["signature"]) == SIGNER
    assert (await wallet.client.get(f"/v3/operations/{op['operation_id']}")).json()[
        "status"
    ] == "CONFIRMED"


async def test_verification_id_partial_full_and_tampered_fields_remain_distinct(wallet):
    await activated(wallet)
    signing = await draft(wallet)
    doc, _ = await confirmed_publication(wallet, signing)
    body = {"request_id": "req_verify", "document_id": doc.document_id, "scope": "ID_ONLY"}
    lookup = await wallet.client.post("/v3/verifications", json=body)
    assert lookup.json()["verification_status"] == "INCONCLUSIVE"
    partial = await wallet.client.post(
        "/v3/verifications",
        json={**body, "scope": "PROTECTED_FIELDS", "candidate": {"amount_minor": 154000}},
    )
    assert partial.json()["comparison_scope"] == "PARTIAL_COMPARISON"
    assert partial.json()["verification_status"] == "INCONCLUSIVE"
    full = await wallet.client.post(
        "/v3/verifications",
        json={**body, "scope": "PROTECTED_FIELDS", "candidate": signing["content"]},
    )
    assert full.status_code == 200, full.text
    assert full.json()["verification_status"] == "VERIFIED"
    for field, value in [
        ("amount_minor", 154001),
        ("payee_account_number", "99999999"),
        ("official_url", "https://attacker.invalid"),
    ]:
        changed = await wallet.client.post(
            "/v3/verifications",
            json={**body, "scope": "PROTECTED_FIELDS", "candidate": {field: value}},
        )
        assert changed.json()["verification_status"] == "TAMPERED", changed.text


@pytest.mark.parametrize("change", ["original", "content", "metadata", "name"])
async def test_database_changes_are_detected_against_chain(wallet, change):
    from originproof_api.wallet_database import WalletDocumentRow

    await activated(wallet)
    signing = await draft(wallet)
    doc, _ = await confirmed_publication(wallet, signing)
    with Session(wallet.engine) as db:
        row = db.get(WalletDocumentRow, ("31337", DOMAIN.verifying_contract, doc.document_id, 1))
        if change == "original":
            row.original += b"\n"
        elif change == "content":
            row.content = row.content | {"amount_minor": 999}
        elif change == "metadata":
            checks = db.get(WalletOnboardingRow, "app_test")
            checks.metadata_value = checks.metadata_value | {"domain": "attacker.invalid"}
        else:
            db.get(IssuerApplicationRow, "app_test").issuer_name = "attacker"
        db.commit()
    result = await wallet.client.post(
        "/v3/verifications",
        json={
            "request_id": "req_changed",
            "document_id": doc.document_id,
            "scope": "PROTECTED_FIELDS",
            "candidate": signing["content"],
        },
    )
    assert result.json()["verification_status"] == "TAMPERED", result.text


async def test_original_comparison_requires_owner_and_checks_exact_bytes(wallet):
    import base64
    import time

    from originproof_api.wallet_database import WalletInputRow

    await activated(wallet)
    signing = await draft(wallet)
    doc, _ = await confirmed_publication(wallet, signing)
    with Session(wallet.engine) as db:
        for suffix, extra in [("same", b""), ("changed", b"\n")]:
            db.add(
                WalletInputRow(
                    input_id="inp_" + suffix,
                    account_id="acct_i",
                    kind="TEXT",
                    original=base64.b64decode(signing["original_base64"]) + extra,
                    accepted_at=int(time.time()),
                    expires_at=int(time.time()) + 3600,
                )
            )
        db.commit()
    body = {
        "request_id": "req_bytes",
        "document_id": doc.document_id,
        "scope": "ORIGINAL_BYTES",
        "original_ref": "inp_same",
    }
    assert (await wallet.client.post("/v3/verifications", json=body)).json()[
        "verification_status"
    ] == "VERIFIED"
    changed = await wallet.client.post(
        "/v3/verifications", json={**body, "original_ref": "inp_changed"}
    )
    assert changed.json()["verification_status"] == "TAMPERED"
    wallet.who["name"] = "other"
    assert (await wallet.client.post("/v3/verifications", json=body)).status_code == 404


async def test_submission_replay_conflict_and_rpc_failure_never_resend(wallet):
    await activated(wallet)
    signing = await draft(wallet)
    body = {
        "request_id": "req_submit",
        "signing_request_id": signing["signing_request_id"],
        "signature": sign(signing),
    }
    wallet.app.state.settings.wallet_relay_enabled = True
    accepted = await wallet.client.post("/v3/publications", json=body)
    assert accepted.json()["status"] == "UNKNOWN"
    retry = await wallet.client.post("/v3/publications", json=body)
    assert retry.json()["operation_id"] == accepted.json()["operation_id"]
    assert len(wallet.chain.sends) == 1
    replay = await wallet.client.post(
        "/v3/publications", json={**body, "signature": "0x" + "00" * 65}
    )
    assert replay.status_code == 409
    wallet.app.state.wallet_runtime.chain = None
    failed = await wallet.client.post(
        "/v3/verifications",
        json={
            "request_id": "req_rpc",
            "document_id": signing["message"]["documentId"],
            "scope": "ID_ONLY",
        },
    )
    assert failed.status_code == 200 and failed.json()["verification_status"] == "INCONCLUSIVE"


async def test_wrong_receipt_cannot_poison_a_signing_request(wallet):
    await activated(wallet)
    signing = await draft(wallet)
    body = {
        "request_id": "req_publish",
        "signing_request_id": signing["signing_request_id"],
        "signature": sign(signing),
    }
    await wallet.client.post("/v3/publications", json=body)
    tx_hash = "0x" + "79" * 32
    wallet.chain.transactions[tx_hash] = WalletTransaction(
        **BLOCK,
        tx_hash=tx_hash,
        sender=APPROVERS[0],
        action="Publish",
        status="CONFIRMED",
        arguments={},
    )
    path = f"/v3/signing-requests/{signing['signing_request_id']}/transactions"
    wrong = await wallet.client.post(
        path,
        json={
            "request_id": "req_bad_receipt",
            "signing_request_id": signing["signing_request_id"],
            "tx_hash": tx_hash,
        },
    )
    assert wrong.status_code == 422
    # A verified actual transaction can still reconcile the original immutable request.
    _, confirmed = await confirmed_publication(wallet, signing)
    assert confirmed["status"] == "CONFIRMED"


async def confirmed_revocation(w, did, version, *, req="req_revoke"):
    response = await w.client.post(
        "/v3/revoke-drafts",
        json={"request_id": "req_revoke_draft_" + req, "document_id": did, "version": version},
    )
    assert response.status_code == 201, response.text
    signing = response.json()
    submitted = await w.client.post(
        "/v3/revocations",
        json={
            "request_id": req,
            "signing_request_id": signing["signing_request_id"],
            "signature": sign(signing),
        },
    )
    assert submitted.status_code == 202, submitted.text
    old = w.chain.documents[(did, version)]
    w.chain.documents[(did, version)] = old.model_copy(
        update={"document": old.document.model_copy(update={"state": "REVOKED"})}
    )
    tx_hash = "0x" + "89" * 32
    message = SigningRequest.model_validate(signing).message
    w.chain.transactions[tx_hash] = WalletTransaction(
        **BLOCK,
        tx_hash=tx_hash,
        sender=APPROVERS[0],
        action="Revoke",
        status="CONFIRMED",
        arguments={"message": message.model_dump(by_alias=True), "signature": sign(signing)},
    )
    accepted = await w.client.post(
        f"/v3/signing-requests/{signing['signing_request_id']}/transactions",
        json={
            "request_id": "req_revoke_tx_" + req,
            "signing_request_id": signing["signing_request_id"],
            "tx_hash": tx_hash,
        },
    )
    assert accepted.status_code == 202 and accepted.json()["status"] == "CONFIRMED", accepted.text


async def test_next_version_preserves_original_and_revoked_latest_does_not_revive_history(wallet):
    from originproof_api.wallet_database import WalletDocumentRow

    await activated(wallet)
    first = await draft(wallet)
    doc1, _ = await confirmed_publication(wallet, first)
    second = await draft(wallet, request_id="req_second", version=2)
    doc2, _ = await confirmed_publication(wallet, second, req="req_publish2", tx_byte="68")
    assert doc1.document_id == doc2.document_id
    await confirmed_revocation(wallet, doc2.document_id, 2)
    latest = await wallet.client.get(f"/v3/documents/{doc2.document_id}")
    assert latest.json()["version"] == 2 and latest.json()["state"] == "REVOKED"
    older = await wallet.client.get(f"/v3/documents/{doc1.document_id}?version=1")
    assert older.json()["state"] == "SUPERSEDED" and older.json()["latest_version"] == 2
    with Session(wallet.engine) as db:
        rows = list(db.query(WalletDocumentRow).order_by(WalletDocumentRow.version))
        assert len(rows) == 2 and rows[0].original != rows[1].original
        assert rows[0].message["version"] == 1 and rows[1].message["version"] == 2


async def test_competing_drafts_and_other_institution_are_rejected(wallet):
    await activated(wallet)
    first = await draft(wallet)
    second = await draft(wallet, request_id="req_competing")

    def body(value, req):
        return {
            "request_id": req,
            "signing_request_id": value["signing_request_id"],
            "signature": sign(value),
        }

    accepted = await wallet.client.post("/v3/publications", json=body(first, "req_first"))
    assert accepted.status_code == 202
    rejected = await wallet.client.post("/v3/publications", json=body(second, "req_second"))
    assert rejected.status_code == 409
    wallet.who["name"] = "other"
    assert (
        await wallet.client.post("/v3/publications", json=body(first, "req_other"))
    ).status_code == 404


async def test_suspension_blocks_publication_but_allows_current_key_revocation(wallet):
    await activated(wallet)
    signing = await draft(wallet)
    doc, _ = await confirmed_publication(wallet, signing)
    wallet.chain.issuers[ISSUER_HASH] = wallet.chain.issuers[ISSUER_HASH].model_copy(
        update={"state": "SUSPENDED"}
    )
    import time

    blocked = await wallet.client.post(
        "/v3/document-drafts",
        json={
            "request_id": "req_suspended",
            "doc_key": identifier_hash("another"),
            "expected_version": 1,
            "expires_at": int(time.time()) + 86400,
            "content": payment_content(),
        },
    )
    assert blocked.status_code == 409 and blocked.json()["detail"] == "ISSUER_SUSPENDED"
    await confirmed_revocation(wallet, doc.document_id, 1)
    result = await wallet.client.post(
        "/v3/verifications",
        json={
            "request_id": "req_suspended_verify",
            "document_id": doc.document_id,
            "scope": "PROTECTED_FIELDS",
            "candidate": signing["content"],
        },
    )
    assert result.json()["verification_status"] == "VERIFIED"
    assert result.json()["document"]["state"] == "REVOKED"
    assert "ISSUER_SUSPENDED" in result.json()["document"]["warnings"]


async def test_retired_key_preserves_past_signature_but_new_issuance_rejects_old_key(wallet):
    from originproof_core.wallet_ports import WalletKey

    await activated(wallet)
    signing = await draft(wallet)
    doc, _ = await confirmed_publication(wallet, signing)
    old_id = doc.key_id
    new_id = identifier_hash("rotated_key")
    new_key = keys.PrivateKey((5).to_bytes(32, "big"))
    wallet.chain.keys[old_id] = wallet.chain.keys[old_id].model_copy(update={"retired_block": "11"})
    wallet.chain.keys[new_id] = WalletKey(
        **(BLOCK | {"block_number": "12"}),
        key_id=new_id,
        issuer_id=ISSUER_HASH,
        signer=new_key.public_key.to_checksum_address().lower(),
        registered_block="11",
    )
    wallet.chain.issuers[ISSUER_HASH] = wallet.chain.issuers[ISSUER_HASH].model_copy(
        update={"key_id": new_id, "signer": new_key.public_key.to_checksum_address().lower()}
    )
    for records in (wallet.chain.issuers, wallet.chain.keys, wallet.chain.documents):
        for identity, value in list(records.items()):
            records[identity] = value.model_copy(update={"block_number": "12"})
    result = await wallet.client.post(
        "/v3/verifications",
        json={
            "request_id": "req_old",
            "document_id": doc.document_id,
            "scope": "PROTECTED_FIELDS",
            "candidate": signing["content"],
        },
    )
    assert result.json()["verification_status"] == "VERIFIED", result.text
    future = await draft(wallet, request_id="req_rotated", version=2)
    old_signature = sign(future)
    rejected = await wallet.client.post(
        "/v3/publications",
        json={
            "request_id": "req_old_key",
            "signing_request_id": future["signing_request_id"],
            "signature": old_signature,
        },
    )
    assert rejected.status_code == 422
    wallet.chain.keys[old_id] = wallet.chain.keys[old_id].model_copy(
        update={"compromise_block": "12"}
    )
    warning = await wallet.client.post(
        "/v3/verifications",
        json={
            "request_id": "req_compromise",
            "document_id": doc.document_id,
            "scope": "PROTECTED_FIELDS",
            "candidate": signing["content"],
        },
    )
    assert "KEY_COMPROMISED" in warning.json()["document"]["warnings"]


async def test_distinct_chain_approvals_are_separate_from_confirmation_of_one_approval(wallet):
    from originproof_core.wallet_contract import ProposalView

    data, _ = await prepared_proposal(wallet)
    pid = data["proposal_id"]
    for i, account in enumerate(("operator", "operator2"), 1):
        view = ProposalView.model_validate(data).model_copy(
            update={"approvals": APPROVERS[:i], "status": "EXECUTED" if i == 2 else "PENDING"}
        )
        wallet.chain.proposals[pid] = WalletProposal(**BLOCK, proposal=view)
        tx_hash = "0x" + str(i) * 64
        wallet.chain.transactions[tx_hash] = WalletTransaction(
            **BLOCK,
            tx_hash=tx_hash,
            sender=APPROVERS[i - 1],
            action="Approve",
            status="CONFIRMED",
            arguments={"proposalId": pid},
        )
        wallet.who["name"] = account
        accepted = await wallet.client.post(
            f"/v3/proposals/{pid}/approvals",
            json={"request_id": f"req_approval_{i}", "tx_hash": tx_hash},
        )
        assert accepted.status_code == 202 and accepted.json()["status"] == "CONFIRMED"
        shown = await wallet.client.get(f"/v3/proposals/{pid}")
        assert shown.json()["status"] == ("EXECUTED" if i == 2 else "PENDING")
    bad = view.model_copy(update={"approvals": [APPROVERS[0], APPROVERS[0]]})
    wallet.chain.proposals[pid] = wallet.chain.proposals[pid].model_copy(update={"proposal": bad})
    assert (await wallet.client.get(f"/v3/proposals/{pid}")).status_code == 503
