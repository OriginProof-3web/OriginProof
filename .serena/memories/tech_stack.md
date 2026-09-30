# Tech Stack

- Python/uv, FastAPI/Pydantic, SQLAlchemy/Alembic/PostgreSQL, Redis/Celery, Solidity/Foundry/OpenZeppelin, Next.js/TypeScript, Docker Compose/GitHub Actions.
- 버전은 .tool-versions, lockfile, Dockerfile이 원본입니다. 메모에 별도 버전을 고정하지 않습니다.
- Analyzer는 LLMProvider와 OpenAI Responses API를 사용합니다. provider 기본은 mock, 모델 기본은 .env.example 및 Analyzer settings를 확인합니다. 기존 개인 .env는 자동 갱신되지 않습니다.
- 표준 Contract 검사·배포는 deployer 컨테이너의 Foundry를 사용합니다. 호스트 forge는 선택이며 fingerprint의 informational 항목입니다.
- 본선 웹과 로컬 EVM은 P0입니다. 외부 로그인·호스팅·테스트넷·OCR는 선택 확장입니다.
