# OriginProof

- 현재 기준: 루트 AGENTS.md → START_HERE.md → docs/development_plan.md v3.0 → docs/adr/0001-finals-contracts.md → 경로별 AGENTS.md. 메모보다 원본 지침을 우선합니다.
- 본선 W1~W7은 개발 단계입니다. 승인된 정책과 실제 구현·연결·단계 완료는 구분합니다.
- P0: 테스트 계정, 두 합성 기관, PAYMENT_REQUEST·OFFICIAL_DOCUMENT, 세 역할 웹, 로컬 EVM. 기존 CARD_PAYMENT_NOTICE와 v1 서명은 회귀 기준입니다.
- AI는 후보 추출만 담당하며 진위·유효성은 결정론적으로 확인합니다. 실제 개인정보를 사용하지 않습니다.
- 의존 방향은 apps/services → packages입니다. 공유 코어에는 HTTP·DB·UI·provider 의존성을 넣지 않습니다.
- API/코어: `mem:backend/core`; Analyzer: `mem:analyzer/core`; 체인: `mem:blockchain/core`; 웹: `mem:web/core`.
- 환경 원본: `mem:tech_stack`; 규칙: `mem:conventions`; 명령: `mem:suggested_commands`; 완료 기준: `mem:task_completion`.
