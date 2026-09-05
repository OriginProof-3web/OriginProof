# Analyzer Agent Instructions

## 1. Scope
Applies to `services/analyzer`. Read the root `AGENTS.md` first.

## 2. Responsibility
M2 owns image or text field extraction, `LLMProvider`, OpenAI and Mock adapters, Pydantic Structured Outputs, prompt versions and extraction evaluation.

## 3. Allowed Changes
Edit analyzer code, prompts and synthetic MVP fixtures. Request shared model changes from M1 after the initial Schema freeze.

## 4. Prohibited Changes
Never decide authenticity, query the Registry as an AI step, expose raw provider output, log API keys or use real bank and card data.

## 5. Contracts
Return `CardPaymentNoticeCandidate` only. Read `OPENAI_MODEL` with default `gpt-5.6-luna`. Keep Provider-specific objects inside the adapter. Use null for absent input fields.

## 6. Required Tests
Run Mock Provider unit tests, normal and changed notice extraction tests, refusal, timeout, incomplete and schema-mismatch tests. Live OpenAI tests are opt-in.

## 7. Completion
Image and text inputs produce the same normalized candidate where applicable. Prompt and model metadata are recorded without storing raw sensitive content.

## 8. Handoff
Report field definition changes to M1 with a sample input, expected Pydantic object and evaluation result.
