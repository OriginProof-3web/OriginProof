# M3/M4 implementation handoff

## Contract identifiers

The human-readable IDs are never stored as plaintext. Integration code must use:

```text
issuer_id = keccak256("iss_origin_mock_bank")
key_id    = keccak256("key_origin_mock_bank_001")
```

## Status mappings

Issuer: `NONE=0`, `ACTIVE=1`, `SUSPENDED=2`, `REVOKED=3`.

Key: `NONE=0`, `ACTIVE=1`, `REVOKED=2`.

Revocation is irreversible. A replacement signing key must receive a new key ID.
`validUntil` is exclusive, so a key is valid when
`validFrom <= timestamp < validUntil`.

## M1 handoff

The API verification service should depend on the `BlockchainReader` protocol.
RPC and decoding failures map to a dependency error; they must produce `ERROR`
with `DEPENDENCY_UNAVAILABLE`, never `NOT_REGISTERED` or `TAMPERED`.

Issuer/key status must remain separate from the final verification status. A
suspended issuer maps to lifecycle `ISSUER_SUSPENDED`; a revoked key maps to
`ISSUER_KEY_REVOKED`.

## Security notes

- Contracts store only opaque IDs, addresses, timestamps, and metadata hashes.
- `DEFAULT_ADMIN_ROLE`, `ISSUER_MANAGER_ROLE`, and `KEY_MANAGER_ROLE` can be
  assigned to separate accounts after deployment.
- The local deployer receives all roles only for deterministic MVP setup.
- Before a public testnet deployment, transfer roles to approved accounts,
  revoke unnecessary deployer roles, run Slither, and record the final manifest.

## Not yet implemented in this slice

`PolicyRegistry` and `ProofStatusRegistry` are outside the minimum M3/M4 scope
defined in the supplied agent guide. They require an agreed M1 schema and a
separate issue before implementation.
