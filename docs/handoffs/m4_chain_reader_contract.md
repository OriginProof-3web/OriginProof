# Handoff: M1 to M4 — BlockchainReader implementation

Requesting role: M1 Backend

Target owner: M4 Blockchain Integration

Blocking issue: the M1 verification core requires a Web3-backed implementation before a proof can
be verified against deployed registries.

Exact interface: `packages/python/originproof_core/ports.py`

Required methods:

```python
async def get_issuer(issuer_id: str) -> IssuerRecord | None
async def get_key(key_id: str) -> KeyRecord | None
async def is_key_valid(key_id: str, at: datetime) -> bool
```

Required mapping:

- Encode contract IDs as `keccak256(utf8(identifier))`, matching M3 tests.
- Map on-chain issuer `ACTIVE`, `SUSPENDED`, `REVOKED` to `IssuerTrustStatus`.
- Map on-chain key `ACTIVE`, `REVOKED`, validity timestamps, issuer ID, and `signer` address to
  `KeyRecord`.
- Return `None` only for an absent record; raise `DependencyUnavailableError` for RPC/ABI/transport
  failures so the API emits `INCONCLUSIVE`, never a false negative.

Required test: validate each port method against deployed local M3 contracts and the Golden Fixture
in `fixtures/golden/card_payment_notice_signing_v1.json`.
