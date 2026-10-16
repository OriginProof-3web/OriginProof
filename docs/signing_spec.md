# MVP signing specification v1

> Scope updated 2026-10-13: the v1/v2 rules below remain historical verification contracts. New institutional wallet signing follows [ADR 0004](adr/0004-v5-governance-wallet-versioning.md) and the planned contract section below. No new runtime/schema support is claimed by this document update.

This specification remains the v1 source of truth for the verifier, registry integration, and
the synthetic issuer. C owns the Python/signing source and B reviews the chain boundary.
It signs a domain-separated digest; it never signs an AI decision or raw user input.

## Algorithm

- Signature: recoverable ECDSA `secp256k1`, 65-byte `r || s || v`
- Hash: Ethereum `Keccak-256` (not NIST SHA3-256)
- Signature scheme: `ECDSA_SECP256K1_KECCAK256_V1`
- Message: the Keccak-256 digest of canonical UTF-8 JSON shown in the Golden Fixture

The verifier accepts Ethereum recovery IDs `0/1` and wallet-style `27/28`, then compares the
recovered address against the active signer returned by `BlockchainReader.get_key`.

## Domain-separated signing payload

The signed object contains these fields and no `signature` field:

`app_domain`, `chain_id`, `expires_at`, `issued_at`, `issuer_id`, `key_id`, `metadata_hash`,
`nonce`, `payload_hash`, `proof_id`, `proof_type`, `schema_version`, `signature_scheme`,
`single_use`, `subject_binding_hash`.

Canonical JSON sorts object keys, uses no insignificant whitespace, normalizes strings to UTF-8
NFC after trimming, and serializes timestamps in UTC RFC 3339 form with `Z`.

## Registry identifier encoding

Contract tests encode issuer and key IDs as `keccak256(utf8(identifier))`. The B-owned Adapter
must use exactly that encoding when translating the string `issuer_id` and `key_id` from the envelope to `bytes32`
contract arguments. The original strings remain in the off-chain proof; only their hash is queried
on chain.

## Golden fixture

Run `make generate` to regenerate
`fixtures/golden/card_payment_notice_signing_v1.json`. B maintains the matching Solidity test
for the end-to-end regression. A change to this fixture, the canonicalization code, or the signing payload is
a shared-contract change and requires review from C and B.

## Finals v2 extension (approved policy, implementation pending)

[ADR 0001](adr/0001-finals-contracts.md) fixes the two new proof types, schema version 2.0.0,
`originproof.finals` domain, recipient binding, status semantics and migration checks. It reuses
the algorithm and envelope signing fields above. It does not change the current card v1 endpoint,
canonicalization or Golden Fixture. C adds separate models/generated fixtures and B cross-checks
them during W1-C3/W3-B2; documentation approval alone does not claim runtime support.

## Extended payment payload draft for development plan v4.0

[ADR 0003](adr/0003-v4-development-baseline.md), section 5, proposes payment schema 3.0.0
with bank/account/holder, purpose, due date, and a per-proof payload commitment nonce.
It preserves the signature algorithm and envelope signing fields above. The document type
and old payment schema 2.0.0 retain their existing rules. C/B must review the draft, generate
versioned models/fixtures, and verify compatibility before enabling new issuance. This is
not a declaration that the current runtime accepts schema 3.0.0.

## 5.0 institutional wallet signing — preparation contract

Updated 2026-10-14: exact proposed fields/types and original generation rules are in
[shared contract v5-shared-0.1](shared_contract_v5.md). Python preparation models, generated
Schema/TypeScript/planned OpenAPI, interface ABI and signing vectors are now available.
Registry/API/browser implementation and B/A/D review remain follow-up work.

The new path uses institution-held keys and EIP-712 business signatures verified by the
new Registry. The app/API does not generate, collect or store institutional private keys.
A relayer may sign gas transactions, but not the institution's business payload.

| Element | Required boundary; final types/encoding need shared Golden review |
| --- | --- |
| EIP-712 domain | Service name, signing version, chainId, verifyingContract |
| Action and ownership | Distinct publish/revoke action, issuerId, docKey, documentId, version, keyId |
| Content | Original-byte SHA-256 and declared protected-field hash, algorithm/schema identifiers |
| Time and replay | issuedAt, expiresAt, institution nonce, submission deadline; atomic nonce consumption |
| documentId | keccak256(abi.encode(issuerId, docKey)); checked against the authenticated institution and fixed owner |

C/B fix exact Solidity types, field names, serialization, supported schema and one set of
browser/Python/Solidity Golden vectors before consumers integrate. Plan version 5.0 is
not a schema number. Do not treat the old payment 3.0.0 proposal as this new contract.

The browser recomputes the original hash and displays protected fields before wallet
signing. Original-byte equality, canonical protected-field equality and ID-only lookup
are separate checks. QR-bearing copies are distinguished from the hash-target original.
Do not change the old Keccak payload hash or existing Golden values to SHA-256.

The Registry checks domain, action, institution/key authority, document ownership,
exact next version, nonce and deadline. New registration, latest pointer update and
superseding the previous latest version are atomic. Revoking the latest version does
not revive a previous version. Retired keys cannot issue new versions; valid historical
signatures and current compromise warnings remain separate.

Normal submission stores the original, signature and Operation before sending. A direct
submission transaction is matched against chain/contract, successful receipt, event and
stored issuer/document/version/hash. Unknown submission results are reconciled before
retrying. A wallet rejection is not a successful issuance.

Required evidence: V5-F04/F05/F06/F07/F08/F09, V5-F19 and V5-F21 in [the plan](development_plan.md),
including cross-language normal/tampered vectors, domain/action replay, owner mismatch,
concurrent next versions, deadline boundaries and unchanged legacy vectors. The preparation models,
generated types/OpenAPI, interface ABI and fixtures are produced from their source files
by scripts/generate_wallet_contracts.py. This does not deploy or enable the new service.
