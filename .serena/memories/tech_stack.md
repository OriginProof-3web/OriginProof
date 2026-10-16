# Tech Stack

- Python/uv, FastAPI/Pydantic, SQLAlchemy/Alembic/PostgreSQL, Redis/Celery, Solidity/Foundry/OpenZeppelin, Next.js/TypeScript, Docker Compose/GitHub Actions.
- 버전은 .tool-versions, lockfile, Dockerfile이 원본입니다. 메모에 별도 버전을 고정하지 않습니다.
- Analyzer는 LLMProvider와 OpenAI Responses API를 사용합니다. provider 기본은 mock, 모델 기본은 .env.example 및 Analyzer settings를 확인합니다. 기존 개인 .env는 자동 갱신되지 않습니다.
- 표준 Contract 검사·배포는 deployer 컨테이너의 Foundry를 사용합니다. 호스트 forge는 선택이며 fingerprint의 informational 항목입니다.
- 기존 스택을 재사용합니다. 공개 EVM은 네트워크/배포 범위를 결정할 목표이며 로컬 성공과 구분합니다. 사용자 입력/STT/OCR은 선정 경로에만 적용하고 외부 로그인·인터넷 호스팅은 자동 필수화하지 않습니다.
