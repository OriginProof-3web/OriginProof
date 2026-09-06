# Web Agent Instructions

## 1. Scope
Applies to `apps/web`. Read the root `AGENTS.md` first.

## 2. Responsibility
This path owns the post-MVP Next.js User App, Issuer Console, Admin views, accessibility and result language.

## 3. Allowed Changes
Use generated TypeScript SDK and feature directories. Begin implementation only after the two-day backend-first MVP Gate.

## 4. Prohibited Changes
Do not duplicate verification rules, call OpenAI directly, store secrets in browser code or label `NOT_REGISTERED` as fake.

## 5. Contracts
Use OpenAPI-generated types. Display Verification Status and Lifecycle Status separately. Keep loading, empty, partial and error states.

## 6. Required Tests
Run TypeScript typecheck, component tests, accessibility checks and Playwright E2E for supported flows.

## 7. Completion
Mobile and desktop flows show accurate evidence and safe next actions without overstating legal or security guarantees.

## 8. Handoff
API contract issues go to the Backend owner with route, request, response and failing generated type.
