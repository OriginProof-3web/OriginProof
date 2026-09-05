# Fixture Agent Instructions

## 1. Scope
Applies to `fixtures`. Read the root `AGENTS.md` first.

## 2. Responsibility
This path owns synthetic issuer, Proof, image, expected-result and Golden Fixture assets.

## 3. Allowed Changes
M2 owns `fixtures/mvp` during the two-day MVP. Shared Golden Fixtures require M1 review.

## 4. Prohibited Changes
No real bank name, logo, phone number, card data, user data, transaction or copied legal document. Do not overwrite a Golden Fixture silently.

## 5. Contracts
Every fixture includes purpose, source=`synthetic`, schema version, expected status and expected reason codes.

## 6. Required Tests
Run Schema validation, image-to-candidate evaluation and expected-result comparison.

## 7. Completion
Normal and tampered fixtures differ in only the intended protected field and reproduce deterministic expected results.

## 8. Handoff
Fixture contract changes include old and new hash, expected result and affected test list.
