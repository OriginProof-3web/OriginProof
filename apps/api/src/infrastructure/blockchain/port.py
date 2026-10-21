from typing import Protocol

from .models import IssuerKeyRecord, IssuerRecord


class BlockchainReader(Protocol):
    async def get_issuer(self, issuer_id: bytes) -> IssuerRecord | None: ...

    async def get_key(self, key_id: bytes) -> IssuerKeyRecord | None: ...
