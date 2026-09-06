# Generated Schema Agent Instructions

## 1. Scope
Applies to `packages/schemas`. Read the root `AGENTS.md` first.

## 2. Responsibility
This path contains generated JSON Schema, TypeScript types and approved blockchain event schemas.

## 3. Allowed Changes
Change source Pydantic models or Contract events first, then run the generator. Commit source and generated diff together.

## 4. Prohibited Changes
Do not hand-edit generated files or create a second enum definition.

## 5. Contracts
Generated output must identify source version and generator command. Breaking changes require an ADR and version update.

## 6. Required Tests
Run generation-diff, fixture validation and compatibility checks.

## 7. Completion
A clean regeneration produces no diff and all consumers compile against the same status and reason-code values.

## 8. Handoff
Send source path, generated diff, affected consumer and migration requirement.
