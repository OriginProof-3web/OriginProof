# W5-C1 — 기존 API 권한·입력·요청 보호

C / @Jordi2801K. 선행 W4-C1 `85e152c`, branch `feat/w5-c-api-security`.
기존 W1~W4-C1 API의 독립 구현·검사 범위입니다. W4-C2/C3 폐기·consume API는 아직 없으며
해당 API의 권한·입력·idempotency·실제 체인 검사는 연결 후 보충합니다.
W5-C2/C3, UI·Contract·indexer 구현과 단계 전체 완료를 포함하지 않습니다.

## 공통 보호와 소비자 계약

`/v1/`, `/v2/` 요청에 다음 보호를 적용합니다. health 경로는 요청 제한에서 제외합니다.

- 실제 연결 peer별 60초 창에서 API 120회, 로그인 10회. 로그인도 API 횟수에 포함하며
  성공·거부·잘못된 입력 모두 계산합니다. 초과는 `429 {"error":"RATE_LIMITED"}`와
  양의 정수 `Retry-After` 초를 반환합니다. 새 요청 ID를 발급하는 근거가 아닙니다.
- JSON 본문 기본 65,536바이트. Content-Length와 실제 streaming 크기를 모두 검사하며
  초과는 `413 REQUEST_TOO_LARGE`, 잘못된 길이는 `400 INVALID_CONTENT_LENGTH`입니다.
  본문 수신 기본 10초 초과는 `408 REQUEST_TIMEOUT`입니다. 응답에 입력을 되돌리지 않습니다.
- 변경/POST 요청의 Origin은 정확한 허용 목록과 비교합니다. `null`·다른 origin은
  `403 ORIGIN_FORBIDDEN`입니다. Origin 없는 CLI는 허용하지만 cross-site Fetch Metadata는
  거부합니다. 인증된 변경의 기존 CSRF 검사는 별도로 유지합니다. 조회형 POST 검증도 Origin을 검사합니다.
- API 응답에 `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`를 적용합니다.
  오류 request ID 헤더는 기존 `req_` 형식과 최대 128문자를 검사합니다.
- `.env.example`의 `API_BROWSER_ORIGINS`는 JSON 배열입니다. localhost/127.0.0.1의
  3000·8000 origin이 기본이며 LAN/HTTPS 사용 시 정확한 origin과 Secure cookie 설정을 맞춥니다.
  횟수·크기·timeout은 `API_REQUESTS_PER_MINUTE`, `API_LOGINS_PER_MINUTE`,
  `API_REQUEST_BODY_MAX_BYTES`, `API_REQUEST_BODY_TIMEOUT_SECONDS`로 조정합니다. 0으로 해제하지 못합니다.

**운영 한계:** 현재 로컬 P0 API의 프로세스 메모리 카운터이며 재시작 때 초기화됩니다.
Docker CMD는 `--workers 1 --no-proxy-headers`로 실행합니다. 직접 기동도 동일 옵션을 사용합니다.
전달 IP 헤더를 인증 근거로 사용하지 않으며 웹 프록시 뒤 사용자는 같은 peer 예산을 공유합니다.
4096개 bucket 상한에서 새 peer는 429로 거부하고 만료 시 정리합니다. 다중 worker/replica나
인터넷 공개 전에 공유 atomic counter와 신뢰할 프록시 정책을 구현해야 합니다.

## 기존 API 전수 권한표

모든 인증 상태는 서버 Account/Session에서 도출합니다. body의 role/issuer/actor 주입은
Pydantic extra=forbid 또는 서버 소유권 검사로 차단합니다. 입력 제한은 기존 모델과 공통 본문 제한을 함께 적용합니다.

| 경로·동작 | 인증·권한 / 객체 범위 | CSRF / 중복·재시도 |
| --- | --- | --- |
| POST `/v1/auth/login` | 준비된 계정 비밀번호; Origin·로그인 제한 | 세션 생성 전 CSRF 없음; 매 로그인 새 세션 |
| GET `/v1/auth/me` | 자기 유효 세션 | 읽기 전용 |
| POST `/v1/auth/logout` | 자기 유효 세션 | CSRF; 세션 삭제 후 재사용 401 |
| POST `/v1/issuer-applications` | 자기 기관 issuer | CSRF; 기관 unique 제약, 중복 409 APPLICATION_EXISTS |
| GET `/v1/issuer-applications/mine` | 자기 기관 issuer | 읽기 전용 |
| GET `/v1/operator/issuer-applications` | operator | 읽기 전용 |
| POST `/v1/operator/issuer-applications/{id}/decision` | operator; 자기 신청 승인 금지 | CSRF; pending 상태/row lock, 재결정 409 |
| POST `/v1/operator/issuer-applications/{id}/activate` | operator; 승인 신청·자기 승인 금지 | CSRF; account/action/request ID·입력 hash |
| POST `/v1/operator/issuers/{id}/{suspend,reactivate,revoke}` | operator; 등록 신청·자기 기관 변경 금지 | CSRF; account/action/request ID·입력 hash |
| GET `/v1/issuer/status` | 자기 기관 issuer | 읽기 전용; 실제 Registry 조회 |
| POST `/v1/issuer/keys`, `/v1/issuer/keys/rotate` | 자기 활성 기관 issuer | CSRF; account/action/request ID·입력 hash; rotate 현재 기간 |
| GET `/v1/issuer/keys`, `/v1/issuer/keys/{id}` | 자기 기관 issuer; 타 기관 key 404 | 읽기 전용 |
| POST `/v1/issuer/keys/{id}/revoke` | 자기 기관 issuer·key; 배포 일치 | CSRF; account/action/request ID·입력 hash |
| GET `/v1/operations/{id}` | 작업 주체·같은 기관 issuer·operator; 타 기관 404 | 읽기 전용; recovery_reference 비공개 |
| POST `/v1/operations/{id}/recover` | 작업 주체 또는 operator; 제출 참조 확인 | CSRF; 동일 저장 Operation/tx 재조회 |
| GET `/v1/audit-events` | issuer는 자기 기관, operator는 운영 이력 | 읽기 전용; recipient 403 |
| GET `/v2/issuer/recipients` | 자기 기관 issuer | 읽기 전용; opaque ID/label만 반환 |
| POST `/v2/issuer/proofs` | 자기 활성 기관 issuer·허용 유형·등록 key·recipient | CSRF; account/request ID·입력 hash·DB unique/lock |
| GET `/v2/issuer/proofs` | 자기 기관 issuer | 읽기 전용; 100개 제한 |
| GET `/v2/proofs/{id}` | 익명 공개 허용 | 읽기 전용; 제한 payload/binding/token/salt 제외 |
| GET `/v2/proofs/{id}/content` | 발행기관 issuer 또는 binding 일치 지정 recipient | 읽기 전용; 타 기관/운영자/다른 recipient 404 |
| POST `/v2/proofs/{id}/verify` | ID 검증 공개; candidate 비교는 content 권한 필요 | 읽기 전용; request ID는 추적이며 consume하지 않음 |
| POST `/v1/mvp/card-notices/verify` | 기존 v1 공개 검증 | 읽기 전용; 기존 Golden/판정 유지 |

## 검사와 미완료

`PYTHONPATH=apps/api/src:packages/python:services/analyzer/src python -m pytest apps/api/tests/test_w5_c_security.py -q`
로 peer/전달 헤더 우회·동시 요청·창 만료·bucket 상한·Origin·streaming 크기·수신 timeout,
기존 변경 경로 전수 미인증/CSRF 거부·Operation/Audit 기관 분리를 확인합니다.
기존 W2/W3/W4 검사에서 요청 ID 충돌·동시 발행·권한/내용 공개 경계를 재사용합니다.

실제 PostgreSQL/Anvil·브라우저·외부 도구 보안 scan·작성자 외 리뷰는 이번 W5 검사에서 수행하지 않았습니다.
하민님 W4-B2/B3 연결 후 W4-C2/C3와 해당 전수 검사를 추가해야 합니다.
형준님은 403/408/413/429 안내와 Retry-After를 연결하고 인준님은 독립 실패 검사를 수행합니다.
기존 B Adapter·서명 계약·migration은 변경하지 않았습니다. OpenAPI는 실제 앱에서 재생성했습니다.
