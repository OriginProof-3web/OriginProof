# W1-D1 — 본선 F01~F15 수용 사례표

기준: [계획서 §16](../development_plan.md), [ADR 0001](../adr/0001-finals-contracts.md).
현재 W1 공식 기준: `0308cb24f9e4aed157095131e2552243767d16eb`, 수정·검증 후보 `f1de961d8f94405d5a143cd853421eee8878b4f1`.
아래 표는 최종 본선 전체 시나리오입니다. 전체 F01~F15의 통과를 주장하지 않습니다.
W1 관련 하위 사례는 실제 연결 검사를 수행했고 [최종 결과](w1-final-verification.md)에 기록했습니다.
F09의 신청/승인 대기 표시, F10의 W1 인증·권한·CSRF·세션/자기 승인 거부, F15의 W1 화면 접근성은 통과했습니다.
키 등록·Proof 발행/변경·consume·전체 rate limit 등 후속 하위 사례는 별도 미실행입니다.

| ID | 역할·입력/조작 | 기대 결과·상태 | 확인 계층·담당 의존성 | 현재 검사와의 차이 |
| --- | --- | --- | --- | --- |
| F01 | 은행/문서 기관 발행자 새 발행 → 지정 수신자 전체 필드 비교 | 두 유형 VERIFIED + ACTIVE, FULL_COMPARISON. W3 NOT_RUN lifecycle은 전체 통과 아님 | A 브라우저, C API/DB/서명, B Registry | v1 카드 정상 검사만 있음; 새 유형 실제 연결 대기 |
| F02 | 지정 수신자가 같은 ID의 금액/문서번호만 변경 | TAMPERED, AMOUNT_MISMATCH 또는 FIELD_MISMATCH; 부족한 입력만 있으면 INCONCLUSIVE | C 코어/API, A 결과 표시 | 카드 금액 회귀 있음; v2 두 유형은 미실행 |
| F03 | 수신자가 issued_at, expires_at 직전, expires_at에 비교 | v2 검사 성공 시 만료 경계에서 VERIFIED + EXPIRED·사용 불가. v1 INCONCLUSIVE + EXPIRED 보존 | C 시계/코어, B 체인 시간, A 표시 | 기존 v1 만료 단위 검사 있음; 실제 v2 경계 미실행 |
| F04 | 수신자/gateway가 같은 Proof 순차·경쟁 consume; 조회 반복; 문서형 consume | 상태 전이/event 1개, 새 요청 ID REPLAY_DETECTED, 같은 ID 기존 Operation, 조회 불변, 문서형 거부 | B Contract 경쟁, C API/DB, A 재조회 | 신규 Registry/Operation 연결 필요 |
| F05 | 은행 발행자가 Office 키/Proof 변경 | API와 Contract 모두 거부, Office 상태 불변 | C 권한/API, B 직접 호출, A 거부 화면 | 타 기관 객체 권한 본선 연결 필요 |
| F06 | 익명 사용자가 없는 Proof/발행자 ID 조회 | NOT_REGISTERED; 위조라고 표시하지 않음 | C 조회/코어, B Reader, A 문구 | v1 오류 경로는 전체 v2 공개 응답 증거가 아님 |
| F07 | 소유 기관 Proof 폐기 → 새 수신자 세션 재검증 | 검사 성공 시 VERIFIED + PROOF_REVOKED, 사용 불가; 캐시에도 반영 | B receipt/상태, C API/캐시, A 새 세션 | 실제 폐기 Registry 미연결 |
| F08 | 발행자 키 정상 교체/기간 종료/유출 폐기, 과거 Proof 조회 | 정상 교체·키 기간 종료는 적법한 과거 Proof 보존. 폐기는 ISSUER_KEY_REVOKED. 미확인 키 신규 발행 거부 | B 키 기간/권한, C 서명/API, A 표시 | 세 시나리오 분리와 현재 상태 조회 필요 |
| F09 | 신청 발행자가 승인 전·DB 승인 후 체인 미확정 상태에서 발행/키 등록 | 거부. 운영 승인+체인 확정 후만 허용; DB 승인≠활성화 | C2/C4 신청·권한, B 상태, A 화면 | W1 신청/승인 대기 실연결 PASS; 키/발행 하위 사례는 후속 |
| F10 | 익명/수신자/자기 신청자가 승인, 무권한 consume; 역할/기관 ID 주입 | 거부·상태 불변. 8시간 세션 만료/logout/CSRF 누락도 변경 거부 | C1/C2/C4 API, B gateway, A 세션 | W1 role/CSRF/세션·자기 승인 거부 PASS; consume은 후속 |
| F11 | 운영자 기관 중지 후 발행 시도·과거 Proof 조회 | 신규 발행 거부, 기존 Proof ISSUER_SUSPENDED·사용 불가 | B Registry, C API, A 표시 | 기관 현재 상태와 서명 검사는 별도 증거 필요 |
| F12 | 등록/발행 timeout 후 동일 request_id 재시도, 다른 입력 재사용 | 기존 Operation 조회, 중복 변화 없음; 입력 충돌 409 REQUEST_ID_CONFLICT | C Operation/DB, B tx/nonce | 외부 전송 전 crash까지 실제 장애 주입 필요 |
| F13 | RPC 장애·receipt 불명·프로세스 재시작·같은 chain ID 재배포 | PENDING/SUBMITTED/UNKNOWN/FAILED 구분; 불명 상태 ACTIVE 금지. 기존 tx 확인 후 복구, 배포 ID 구분 | B RPC/indexer/manifest, C 복구, A 대기 | in-memory 예외만으로 실제 장애 복구를 인정하지 않음 |
| F14 | 다른 수신자, 다른 domain/chain ID로 비교 또는 재사용 | 권한/binding 거부, DOMAIN_MISMATCH/NETWORK_MISMATCH, 필수 실패 후 의존 검사 NOT_RUN | C 권한/코어, B gateway, A 오류 | 실제 v2 모델과 인증 계정 연결 필요 |
| F15 | 익명/권한 없는 계정 공개 조회·비교, 키보드 사용, 과도한 요청 | 개인키/token/salt/binding/제한 payload 비노출, 운영자도 자동 열람 불가, 접근성·rate limit 동작 | C 응답/로그/요청제한, A 브라우저, B 온체인 내용 | W1 로그인·승인 화면 axe PASS; v2 공개 응답·과도 요청 제한은 후속 |

## 수용 검사의 기록 방법

각 실행에서 `case ID / 검증 SHA / 환경 fingerprint / 계약·fixture 버전 /
actor / 입력 변경 / 기대값 / 실제값 / PASS·FAIL·NOT_RUN / 실행 계층 /
실패 담당 / 증거 경로`를 남긴다. 제한 필드 원문·비밀값은 증거에 넣지 않는다.

같은 정책의 우선순위 조합도 추가 검증한다:
PROOF_REVOKED → ISSUER_KEY_REVOKED → ISSUER_SUSPENDED → CONSUMED → EXPIRED → ACTIVE.
대표 상태 외 모든 확인 원인을 보존하며 RPC 실패 시 lifecycle은 null이다.
실제 불일치와 누락이 함께 있으면 TAMPERED가 우선한다.

W1-D2 입력은 [fixtures/finals](../../fixtures/finals/README.md)에 있다.
API URL/생성 모델 확정은 C, 체인 직접 호출/receipt 계약은 B, 브라우저 UI는 A와 연결한다.
사용자가 W1 완료 준비 1~5번을 지시해 실제 browser QA와 발견 결함 수정에 필요한 경로를 함께 변경했습니다. F16 OCR/PDF는 채택되지 않은 P1로 보류한다.
