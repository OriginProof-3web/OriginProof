# Backend and Shared Python Core

- C: blockchain Adapter 외 apps/api 및 packages/python/originproof_core. B: apps/api/src/infrastructure/blockchain.
- API는 인증·권한·기관·소유권 확인, 요청 조율, 저장·migration·검증 응답을 담당합니다. 세션은 요청/작업 범위로 관리합니다.
- 코어는 원본 Pydantic 모델·canonicalization·서명·결정론적 규칙을 담당하며 HTTP·DB·UI·provider를 의존하지 않습니다.
- v1/v2 계약·서명 원본을 보존합니다. 신규 문서/버전·기관 지갑 서명·공동승인·Operation은 ADR 0004로 연결하고 서버가 신규 기관키를 생성/보관하지 않습니다. 현재 코드 준비 여부는 테스트와 PR에서 확인합니다.
- verification status와 lifecycle·사용 가능성을 구분합니다. DB 승인·제출 hash만으로 체인 성공을 선언하지 않습니다.
