# MVP signing specification v1

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
