# API Agent Instructions

## 1. 적용 범위와 담당

`apps/api/`에 적용하며 루트 `AGENTS.md`를 먼저 읽습니다.

C가 인증·기관 신청/권한·발행·조회·검증·Operation/AuditEvent와 DB migration을 담당합니다. `src/infrastructure/blockchain/`는 B 소유이며 C의 orchestration과 구분합니다. 새 세션·권한 정책과 Proof 정책은 본선 ADR을 따릅니다.

## 2. 구현·계약 규칙

Pydantic 계약과 기존 코어·ports를 재사용하고 request/task마다 별도 SQLAlchemy AsyncSession을 사용합니다. 외부 변경 전 Operation을 저장하고 동일 요청 ID의 내용 충돌·동시 재시도·미확인 제출을 처리합니다. DB 승인·mock 성공을 체인 완료로 반환하지 않습니다.

기관·키·Proof 소유권과 CSRF·수신자 권한을 서버에서 검사합니다. 공개 조회는 허용 필드만 반환하며 제한 payload·개인키·인증정보를 노출하지 않습니다. 조회와 consume을 분리하고 현재 체인 상태 불명확 시 사용 가능 판정을 보류합니다.

## 3. 검증과 완료

API/코어 단위·async HTTP 검사, 권한·동시 요청·저장 실패·재시작 복구, 관련 migration을 검사합니다. 실제 PostgreSQL·Adapter 연결 결과는 mock과 구분합니다. 변경한 API의 OpenAPI·생성 타입과 기존 카드 회귀를 확인합니다.

## 4. 인계

A에게 요청·응답·오류 예시를, B에게 필요한 Reader/Writer·확정/재조회 경계를 전달합니다. API가 독립 구현되었어도 실제 Adapter·웹 연결 수용 기준이 남으면 해당 부분은 대기로 보고합니다.
