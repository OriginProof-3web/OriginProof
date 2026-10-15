"""Real SQLAlchemy storage/HTTP and signed inputs; Registry evidence is synthetic."""

import hashlib
from types import SimpleNamespace

import pytest
from eth_keys import keys
from httpx import ASGITransport, AsyncClient
from originproof_api.accounts import current_session
from originproof_api.database import AccountRow, Base, IssuerApplicationRow
from originproof_api.main import create_app
from originproof_api.settings import Settings
from originproof_api.wallet_database import WalletOnboardingRow
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
    )
    app = create_app(database=database, settings=settings, wallet_chain=chain)
    who = {"name": "issuer"}

    async def identity():
        return accounts[who["name"]], SimpleNamespace(csrf_token="csrf")

    app.dependency_overrides[current_session] = identity
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


async def test_email_failure_and_reissue_limits_persist(wallet):
    c = wallet.client
    path = "/v3/issuer-applications/app_test/"
    assert (
        await c.post(path + "email-codes", json={"email": "staff@bank.example.invalid"})
    ).status_code == 201
    assert (
        await c.post(path + "email-codes", json={"email": "staff@bank.example.invalid"})
    ).status_code == 429
    with Session(wallet.engine) as db:
        row = db.get(WalletOnboardingRow, "app_test")
        salt = "synthetic"
        row.code_hash = salt + ":" + hashlib.sha256((salt + "123456").encode()).hexdigest()
        db.commit()
    for _ in range(5):
        assert (
            await c.post(path + "email-verifications", json={"code": "000000"})
        ).status_code == 422
    assert (await c.post(path + "email-verifications", json={"code": "123456"})).status_code == 429


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
