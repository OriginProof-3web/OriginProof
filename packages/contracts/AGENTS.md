# Contract Agent Instructions

## 1. 적용 범위와 담당

`packages/contracts/`에 적용하며 루트 `AGENTS.md`를 먼저 읽습니다.

B가 Issuer/Key/ProofStatus Registry, 권한·상태 전이·event, Foundry 검사·배포 script·ABI를 담당합니다. Contract와 배포/Adapter의 변경 및 검증 증거를 구분합니다.

## 2. 구현·계약 규칙

기존 Registry와 ID 인코딩을 재사용하고 C와 Python/ABI 경계를 맞춥니다. 원문·개인정보·계정 ID·salt·전체 payload·개인키는 온체인에 넣지 않습니다. 발행키와 Registry 운영권한을 분리하고 폐기 키는 재활성화하지 않습니다.

본선 ADR의 등록 commitment·서버 대행 인증 신뢰 경계·Proof 소유권·binding·기간·상태 검사를 구현합니다. consume은 체인의 원자적 상태 전이이며 API를 우회한 무권한 호출도 거부합니다. 조회는 상태를 바꾸지 않습니다. 계획의 함수명은 배포된 ABI가 아니므로 실제 생성 ABI·manifest를 함께 전달합니다.

## 3. 검증과 완료

Foundry 정상·권한·경계·fuzz 검사와 consume 경쟁/재사용·직접 호출·타 기관 폐기·위조 commitment 사례를 검사합니다. 실패/동시성은 receipt와 최종 상태로 입증합니다. C와 Golden Fixture·domain 호환성을 확인합니다.

## 4. 인계

ABI/event diff·버전·배포/migration 영향·실행 SHA·실제 검사 결과를 C와 Adapter 소비자에게 전달합니다. Contract 단위 성공을 API·웹 전체 완료로 표현하지 않습니다.
