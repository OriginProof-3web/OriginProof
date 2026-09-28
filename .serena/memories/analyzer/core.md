# Analyzer

- `services/analyzer` owns image/text extraction, prompts, `LLMProvider`, OpenAI and Mock adapters, and extraction evaluation.
- Return `CardPaymentNoticeCandidate` only; absent fields are null. Never decide authenticity, query registry state, or leak provider objects/raw output.
- Read model/provider, reasoning, timeout and retries from settings; default model is `gpt-5.6-luna`.
- Validate image/file signature, MIME, size and page count before processing; keep logs free of keys, full images, and raw private data.
- Tests use Mock provider by default. Live OpenAI tests are opt-in.