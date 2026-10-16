from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from .models import SignedProofEnvelope


class IssuerTrustStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class KeyTrustStatus(StrEnum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class IssuerRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issuer_id: str
    status: IssuerTrustStatus


class KeyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_id: str
    issuer_id: str
    signer: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    status: KeyTrustStatus
    valid_from: datetime
    valid_until: datetime


class ProofRepository(Protocol):
    async def get_proof(self, proof_id: str) -> SignedProofEnvelope | None: ...


class BlockchainReader(Protocol):
    """Port owned by M1; the Web3 implementation is supplied by M4."""

    async def get_issuer(self, issuer_id: str) -> IssuerRecord | None: ...

    async def get_key(self, key_id: str) -> KeyRecord | None: ...

    async def is_key_valid(self, key_id: str, at: datetime) -> bool: ...


class DependencyUnavailableError(RuntimeError):
    """A repository, RPC, or dependency could not produce a trustworthy answer."""
