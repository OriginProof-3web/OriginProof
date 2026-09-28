# MVP signing specification v1

This specification is the source of truth for the M1 verifier, M3/M4 registry integration, and
the synthetic issuer. It signs a domain-separated digest; it never signs an AI decision or raw
user input.

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

M3 contract tests encode issuer and key IDs as `keccak256(utf8(identifier))`. M4 must use exactly
that encoding when translating the string `issuer_id` and `key_id` from the envelope to `bytes32`
contract arguments. The original strings remain in the off-chain proof; only their hash is queried
on chain.

## Golden fixture

Run `make generate` to regenerate
`fixtures/golden/card_payment_notice_signing_v1.json`. M4 must add a matching Solidity test before
the end-to-end demo. A change to this fixture, the canonicalization code, or the signing payload is
a shared-contract change and requires review from M1 and M4.
