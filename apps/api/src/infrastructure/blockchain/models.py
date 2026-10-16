from dataclasses import dataclass
from enum import IntEnum


class IssuerStatus(IntEnum):
    NONE = 0
    ACTIVE = 1
    SUSPENDED = 2
    REVOKED = 3


class KeyStatus(IntEnum):
    NONE = 0
    ACTIVE = 1
    REVOKED = 2


@dataclass(frozen=True, slots=True)
class IssuerRecord:
    issuer_id: bytes
    account: str
    metadata_hash: bytes
    status: IssuerStatus


@dataclass(frozen=True, slots=True)
class IssuerKeyRecord:
    key_id: bytes
    issuer_id: bytes
    signer: str
    valid_from: int
    valid_until: int
    status: KeyStatus

    def is_valid_at(self, timestamp: int, issuer_status: IssuerStatus) -> bool:
        return (
            self.status is KeyStatus.ACTIVE
            and issuer_status is IssuerStatus.ACTIVE
            and self.valid_from <= timestamp < self.valid_until
        )
