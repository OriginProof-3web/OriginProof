# Shared Python Core Agent Instructions

## 1. 적용 범위와 담당

`packages/python/`에 적용하며 루트 `AGENTS.md`를 먼저 읽습니다.

C가 Pydantic 도메인 모델·정규화·서명·결정론적 검증·reason codes 및 생성 Schema 원본을 담당하고 B가 체인·서명 경계를 검토합니다.

## 2. 구현·계약 규칙

기존 v1 카드 모델·Golden Fixture·판정을 보존하며 본선 두 유형·새 버전 정책은 ADR로 구분합니다. 기존 v1/v2의 NFC·정렬 JSON·서명 결과는 보존합니다. 신규 EIP-712·원본 SHA-256·보호 필드 hash·documentId/version은 ADR 0004와 서명 명세의 새 계약으로 추가하고 브라우저/Python/Solidity Golden을 대조합니다. 계획 5.0을 schema 버전으로 자동 사용하지 않습니다. 생성물은 원본 변경과 함께 갱신합니다.

FastAPI·SQLAlchemy·OpenAI/Web3 객체나 직접 파일/네트워크 접근을 넣지 않습니다. 외부 조회는 ports로 주입합니다. 검사에 사용한 시각·조회 결과를 명확히 하고 서명 성공, 내용 비교 범위, 현재 사용 가능 상태, 미실행 검사를 분리합니다. 타입/enum이 존재한다고 기능 완료로 보지 않습니다.

## 3. 검증과 완료

모델 검증·정규화·Golden hash·서명/domain·기간 경계·상태 우선순위·누락 필드 검사를 수행합니다. 정상 키 교체/유출 폐기·v1 회귀와 새 두 유형의 결과표를 각각 확인합니다. B와 교차 검증 전에는 체인 호환 완료로 기록하지 않습니다.

## 4. 인계

모델/서명 변경은 old/new 예시·version·호환 영향·생성 명령·필수 검사를 A/B/D에 공유합니다. 소비자 구현과 연결하는 시점의 기준 SHA를 명시합니다.
