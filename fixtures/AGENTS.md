# Fixture Agent Instructions

## 1. 적용 범위와 담당

`fixtures/`에 적용하며 루트 `AGENTS.md`를 먼저 읽습니다.

D가 합성 입력·사례·기대 결과를 관리합니다. 서명 Golden Fixture는 C 생성기를 사용하고 B가 체인 호환성을 검토합니다.

## 2. 구현·계약 규칙

실제 기관명·로고·전화·카드·개인·거래 자료를 사용하지 않습니다. purpose·synthetic 출처·schema version·기대 상태/사유의 근거를 fixture 또는 대응 manifest에 기록합니다. Golden Fixture는 조용히 덮어쓰지 않습니다.

두 유형·두 기관·권한/기간/상태/binding 사례는 ADR과 F01~F15를 따릅니다. 정상/변조 사례는 의도한 필드만 달라야 합니다. 기존 카드 회귀와 새 본선 사례를 구분하고 미래 기능은 미실행으로 기록합니다.

## 3. 검증과 완료

Schema·Golden hash·기대 결과·기간 경계를 검사합니다. 이미지-to-candidate 평가는 관련 추출 변경/P1 범위일 때만 수행합니다. 타 담당 테스트 경로는 handoff 또는 사용자 지시에 따라 협업합니다.

## 4. 인계

source version·생성 명령·old/new hash·변경한 기대 결과·영향받는 검사를 전달합니다. AI 평가 점수로 최종 진위 검사를 대신하지 않습니다.
