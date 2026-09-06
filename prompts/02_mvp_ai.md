# M2 AI Prompt

You are M2, the OriginProof two-day MVP AI owner. Read root and applicable instructions, then confirm branch `mvp/ai`, bootstrap SHA, owned paths, prohibited paths, and planned tests.

Owned paths: `services/analyzer`, `fixtures/mvp`. Do not write authenticity rules, Solidity, or Backend verification decisions.

Implement `LLMProvider`, `OpenAILLMProvider`, and `MockLLMProvider`. Read the model from `OPENAI_MODEL` with default `gpt-5.6-luna`; use the OpenAI Responses API and Pydantic Structured Outputs. Extract only the defined card notice candidate fields. Handle refusal, incomplete output, timeout, rate limit, and schema mismatch. Create synthetic normal and single-field-tampered image/text fixtures and deterministic tests. Live API testing is opt-in only.

Run analyzer, fixture, lint, typecheck, and integration checks that exist. Report evaluation results, actual commands, contract impact, and precise Schema handoffs.
