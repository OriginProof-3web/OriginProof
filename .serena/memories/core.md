# OriginProof

- 현재 기준: 루트 AGENTS.md → START_HERE.md → docs/development_plan.md 최신 버전 → docs/adr/0004-v5-governance-wallet-versioning.md → 경로별 AGENTS.md. 메모보다 원본 지침을 우선합니다.
- 본선 W1~W7은 개발 단계입니다. 승인된 정책과 실제 구현·연결·단계 완료는 구분합니다.
- 신규 기준: 두 합성 기관/안내 템플릿·세 역할 웹, 2-of-3·기관 지갑 서명·문서 버전·통합 결과. v1/v2 서명·binding·consume은 구버전 회귀입니다. 입력은 팀 결정 전 미정, Decisions API는 범위 밖 후속 검토입니다.
- AI는 선정 입력의 추출·피싱 위험/근거 설명을 담당하며 발행·내용·현재 상태는 결정론적으로 확인합니다. 실제 개인정보를 사용하지 않습니다.
- 의존 방향은 apps/services → packages입니다. 공유 코어에는 HTTP·DB·UI·provider 의존성을 넣지 않습니다.
- API/코어: `mem:backend/core`; Analyzer: `mem:analyzer/core`; 체인: `mem:blockchain/core`; 웹: `mem:web/core`.
- 환경 원본: `mem:tech_stack`; 규칙: `mem:conventions`; 명령: `mem:suggested_commands`; 완료 기준: `mem:task_completion`.

- 공통 준비 계약은 `docs/shared_contract_v5.md` v5-shared-0.1 및 `originproof_core.wallet_contract`/`wallet_signatures`입니다. 생성 타입/OpenAPI·인터페이스 ABI·Golden을 재사용하고 기존 v1/v2 API와 분리합니다. B/A/D 리뷰·실제 연결은 미완료이며 초안을 별도로 재정의하지 않습니다.
