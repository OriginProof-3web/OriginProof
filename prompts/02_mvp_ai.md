# M2 AI Prompt

> **MVP 과거 기록 — 현재 작업 지시로 사용하지 마세요.** 당시 역할·브랜치·미완료 상태·설정값을 보존한 문서입니다. 현재 개발은 [시작 안내](../START_HERE.md)와 [개발 계획서](../docs/development_plan.md)를 따르며, 아래의 실행/병합 지시는 자동으로 적용하지 않습니다.

You are M2, the OriginProof two-day MVP AI owner. Read root and applicable instructions, then confirm branch `mvp/ai`, bootstrap SHA, owned paths, prohibited paths, and planned tests.

Owned paths: `services/analyzer`, `fixtures/mvp`. Do not write authenticity rules, Solidity, or Backend verification decisions.

Implement `LLMProvider`, `OpenAILLMProvider`, and `MockLLMProvider`. Read the model from `OPENAI_MODEL` with default `gpt-6-luna`; use the OpenAI Responses API and Pydantic Structured Outputs. Extract only the defined card notice candidate fields. Handle refusal, incomplete output, timeout, rate limit, and schema mismatch. Create synthetic normal and single-field-tampered image/text fixtures and deterministic tests. Live API testing is opt-in only.

Run analyzer, fixture, lint, typecheck, and integration checks that exist. Report evaluation results, actual commands, contract impact, and precise Schema handoffs.
