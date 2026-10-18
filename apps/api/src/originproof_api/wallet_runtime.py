"""Shared v3 session, immutable requests and chain evidence boundaries."""

import asyncio
import hashlib
import time
from uuid import uuid4

from fastapi import HTTPException
from originproof_core import DependencyUnavailableError
from originproof_core.wallet_contract import Hex32, OperationView, SigningRequest, WalletDomain
from originproof_core.wallet_ports import (
    WalletDocument,
    WalletIssuer,
    WalletKey,
    WalletProposal,
    WalletTransaction,
)
from originproof_core.wallet_signatures import identifier_hash
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .accounts import require_csrf
from .database import AccountRow, AuditEventRow, OperationRow
from .operations import input_fingerprint, require_retained_operation
from .wallet_database import WalletRequestRow, WalletSigningRow


def now():
    return int(time.time())


def sha256(value):
    return "0x" + hashlib.sha256(value).hexdigest()


class WalletRuntime:
    def __init__(self, database, settings, chain=None):
        self.database, self.settings, self.chain = database, settings, chain

    @property
    def domain(self):
        if not self.settings.wallet_registry_address:
            raise HTTPException(503, "WALLET_REGISTRY_NOT_CONFIGURED")
        return WalletDomain(
            chainId=str(self.settings.blockchain_chain_id),
            verifyingContract=self.settings.wallet_registry_address,
        )

    async def rpc(self, method, *args):
        if self.chain is None:
            raise HTTPException(503, "WALLET_REGISTRY_UNAVAILABLE")
        try:
            result = await asyncio.wait_for(getattr(self.chain, method)(*args), timeout=10)
            if method == "submit" and result is not None:
                result = TypeAdapter(Hex32).validate_python(result)
            model = {
                "issuer": WalletIssuer,
                "key": WalletKey,
                "document": WalletDocument,
                "proposal": WalletProposal,
                "transaction": WalletTransaction,
                "find_transaction": WalletTransaction,
            }.get(method)
            if result is not None and model:
                result = model.model_validate(
                    result.model_dump() if hasattr(result, "model_dump") else result
                )
                if hasattr(result, "verifying_contract") and (
                    result.chain_id != self.domain.chain_id
                    or result.verifying_contract != self.domain.verifying_contract
                ):
                    raise ValueError("chain evidence does not match trusted deployment")
            return result
        except (DependencyUnavailableError, TimeoutError, ValueError, ValidationError):
            raise HTTPException(503, "WALLET_REGISTRY_UNAVAILABLE") from None

    def authorize(self, request, identity, role=None, *, mutation=True):
        account, session = identity
        if mutation:
            require_csrf(request, session)
        if role and account.role != role:
            raise HTTPException(403, "FORBIDDEN")
        if role == "issuer" and not account.issuer_id:
            raise HTTPException(403, "FORBIDDEN")
        return account

    async def lock_account(self, db, account):
        await db.scalar(
            select(AccountRow).where(AccountRow.account_id == account.account_id).with_for_update()
        )

    def issuer_id(self, account):
        if not account.issuer_id:
            raise HTTPException(403, "FORBIDDEN")
        return identifier_hash(account.issuer_id)

    async def operator(self, request, identity, *, mutation=True):
        account = self.authorize(request, identity, "operator", mutation=mutation)
        address = self.settings.wallet_operator_addresses.get(account.account_id)
        if not address or await self.rpc("is_approver", address) is not True:
            raise HTTPException(403, "APPROVER_REQUIRED")
        return account, address

    async def signing_retry(self, db, account, kind, body):
        row = await db.scalar(
            select(WalletSigningRow).where(
                WalletSigningRow.account_id == account.account_id,
                WalletSigningRow.kind == kind,
                WalletSigningRow.request_id == body.request_id,
            )
        )
        if row:
            if row.input_hash != input_fingerprint(body.model_dump(mode="json")):
                raise HTTPException(409, "REQUEST_ID_CONFLICT")
            if now() >= row.expires_at:
                raise HTTPException(410, "SIGNATURE_EXPIRED")
        return row

    async def save_signing(self, db, account, kind, body, signing):
        row = WalletSigningRow(
            signing_request_id=signing.signing_request_id,
            account_id=account.account_id,
            issuer_id=self.issuer_id(account),
            kind=kind,
            request_id=body.request_id,
            input_hash=input_fingerprint(body.model_dump(mode="json")),
            payload=signing.model_dump(mode="json", by_alias=True),
            expires_at=signing.message.deadline,
        )
        db.add(row)
        await self.commit(db)
        return signing

    async def owned_signing(self, db, account, request_id, kind=None):
        row = await db.scalar(
            select(WalletSigningRow)
            .where(
                WalletSigningRow.signing_request_id == request_id,
            )
            .with_for_update()
        )
        if row is None or row.account_id != account.account_id or (kind and row.kind != kind):
            raise HTTPException(404, "SIGNING_REQUEST_NOT_FOUND")
        signing = SigningRequest.model_validate(row.payload)
        if signing.domain != self.domain:
            raise HTTPException(409, "DEPLOYMENT_CHANGED")
        return row, signing

    async def commit(self, db):
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(409, "REQUEST_ID_CONFLICT") from None

    def audit(self, db, account, action, target, status):
        db.add(
            AuditEventRow(
                event_id=f"evt_{uuid4().hex}",
                actor_account_id=account.account_id,
                issuer_id=account.issuer_id,
                action=action,
                target_id=target,
                after_status=status,
            )
        )

    def operation_view(self, row):
        require_retained_operation(row, now())
        pending = row.status in ("PENDING_SUBMISSION", "UNKNOWN", "SUBMITTED")
        intent = row.input_body or {}
        next_action = "RECONCILE" if pending else "NONE"
        if row.error_code == "SIGNATURE_EXPIRED":
            next_action = "RESIGN"
        return OperationView(
            operation_id=row.operation_id,
            request_id=row.request_id,
            status=row.status,
            tx_hash=row.tx_hash,
            document_id=intent.get("document_id"),
            version=intent.get("version"),
            recovery_required=pending,
            next_action=next_action,
        )

    async def lock_operation(self, db, operation_id, tx_hash=None):
        row = await db.get(OperationRow, operation_id)
        if row is None:
            raise HTTPException(410, "RESULT_EXPIRED")
        signing_id = (row.input_body or {}).get("signing_request_id")
        if signing_id:
            # Keep the signing -> operation order used by direct intake, including FK writes.
            await db.scalar(
                select(WalletSigningRow)
                .where(WalletSigningRow.signing_request_id == signing_id)
                .with_for_update()
            )
        row = await db.scalar(
            select(OperationRow)
            .where(OperationRow.operation_id == operation_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if row is None:
            raise HTTPException(410, "RESULT_EXPIRED")
        require_retained_operation(row, now())
        if tx_hash and row.tx_hash and row.tx_hash != tx_hash:
            raise HTTPException(409, "DIRECT_TX_ALREADY_BOUND")
        return row

    async def operation_retry(self, db, account, action, body):
        claim = await db.get(WalletRequestRow, (account.account_id, action, body.request_id))
        if claim:
            if claim.input_hash != input_fingerprint(body.model_dump(mode="json")):
                raise HTTPException(409, "REQUEST_ID_CONFLICT")
            row = await db.get(OperationRow, claim.resource_id)
            if row is None:
                raise HTTPException(410, "RESULT_EXPIRED")
            require_retained_operation(row, now())
            return row
        row = await db.scalar(
            select(OperationRow)
            .where(
                OperationRow.account_id == account.account_id,
                OperationRow.action == action,
                OperationRow.request_id == body.request_id,
            )
            .with_for_update()
        )
        if row and row.input_hash != input_fingerprint(body.model_dump(mode="json")):
            raise HTTPException(409, "REQUEST_ID_CONFLICT")
        if row:
            require_retained_operation(row, now())
        return row

    def operation(self, db, account, action, body, target, intent):
        row = OperationRow(
            operation_id=f"op_{uuid4().hex}",
            account_id=account.account_id,
            issuer_id=account.issuer_id,
            action=action,
            request_id=body.request_id,
            input_hash=input_fingerprint(body.model_dump(mode="json")),
            input_body=intent,
            target_id=target,
            status="PENDING_SUBMISSION",
            deployment_id=self.domain.verifying_contract,
            recovery_reference={"domain": self.domain.model_dump(by_alias=True)},
        )
        db.add(row)
        self.audit(db, account, action, target, row.status)
        return row


def runtime(request):
    return request.app.state.wallet_runtime
