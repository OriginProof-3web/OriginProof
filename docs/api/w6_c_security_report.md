# W6-C2 — API 보안 검사와 개발 기록

**2026-10-03 최신 상태:** W4 신규 API 연결, W6 C1~C3 구현·실제 복구 검증과
공유 의존성 보안 패치를 마쳤습니다. [최신 검증·한계](../portfolio/W6-C.md)와
[복구 runbook](w6_c_recovery_runbook.md)을 기준으로 봅니다. 아래 본문은 2026-10-01 초기 기록입니다.

C / @Jordi2801K. 선행 W5-C1 `b6d7d67`, branch `feat/w6-c-security-checks`.
현재 존재하는 API·세션·DB 오류·서명기 파일의 독립 구현·검사 결과입니다.
W4-C2/C3와 실제 Contract 우회 검증·브라우저·팀원 독립 리뷰를 완료했다고 표현하지 않습니다.

## 구현과 확인한 동작

| 항목 | 결과·근거 |
| --- | --- |
| 세션 | 8시간 고정 만료와 경계 거부, token hash만 DB 저장, logout 후 cookie 재사용 401. 43자 URL-safe 형식이 아닌 cookie는 DB 접근 전 거부합니다. |
| Cookie | host-only·HttpOnly·SameSite=Lax·8시간. 실제 HTTPS 요청은 설정 기본값과 무관하게 Secure입니다. HTTPS 프록시의 내부 HTTP 연결은 `API_SESSION_COOKIE_SECURE=true`가 필요합니다. |
| CSRF | 모든 기존 변경 경로의 누락·오류 token 거부를 W5 전수 검사로 확인합니다. 현재 세션과 다른 로그인 CSRF token 거부, 비ASCII 헤더도 예외 대신 403으로 거부합니다. |
| 로그인 | 미등록 계정도 dummy hash로 비밀번호 계산을 수행하고 동일 401을 반환합니다. 기존 PBKDF2를 thread pool에서 수행합니다. 완전한 시간 동일성을 측정/보장한 것은 아닙니다. |
| 역할·기관 | body/header의 role·account·기관 주입으로 서버 권한을 바꾸지 못합니다. Operation/Audit 기관 분리 및 Proof 제한 조회/비교 검사는 기존 W2/W3와 W5 검사를 재사용합니다. |
| 로그·응답 | 잘못된 입력·로그인·계정 응답에 password/hash·입력 marker가 없습니다. SQLAlchemy `hide_parameters=True`로 SQL 오류의 bind values를 숨기며 실제 SQLite unique 오류 문자열로 확인했습니다. CSRF 값과 session cookie는 인증 흐름의 정해진 응답에만 제공합니다. |
| 키 파일 | 0700 directory·0600 file·같은 UID·일반 파일·단일 hard link·정상 32바이트 scalar·challenge signer 대응을 확인합니다. traversal·symlink·hard link·FIFO·권한/소유자 오류·잘못된 키를 거부합니다. |
| 파일 경합 | directory descriptor 기준 상대 open/create/fsync로 경로 교체 경합을 막습니다. 검사 중 directory를 교체해도 원래 descriptor의 키를 읽는 재현 검사가 통과합니다. FIFO는 nonblocking open 뒤 일반 파일 검사로 거부합니다. |
| 요청 제한 | W5의 peer별 API/로그인·Origin·본문 크기/수신 timeout·cache 보호를 재사용합니다. [설정·오류 계약·단일 worker 한계](w5_c_security_contract.md)를 따릅니다. |

## 검사와 실제 범위

Python 3.13/macOS, 합성 계정·실제 HTTP ASGI·SQLite 저장·임시 파일 기준입니다.
실행 명령은 현재 checkout의 코드와 고정 dependency가 설치된 Python에서 수행합니다.

```sh
PYTHONPATH=apps/api/src:packages/python:services/analyzer/src python -m pytest -q
PYTHONPATH=apps/api/src:packages/python:services/analyzer/src python -m pytest apps/api/tests/test_w5_c_security.py apps/api/tests/test_w6_c_security.py -q
ruff check apps packages/python services scripts
PYTHONPATH=apps/api/src:packages/python:services/analyzer/src python -m compileall -q apps/api/src packages/python services scripts
git diff --check
```

OpenAPI 변경은 없으며 생성 파일과 실제 앱의 동등성을 확인합니다.
최종 전체 Python 228 passed / opt-in 4 skipped, W5 31개와 W6 18개 보안 사례를 포함합니다.
Ruff·compileall·diff 검사와 보호 설정의 0 값 거부 검사가 통과했습니다.
실제 PostgreSQL/Anvil 검사는 환경 미설정으로 opt-in skip이며 브라우저·다른 노트북 재현·
Contract 직접 호출·외부 dependency/secret scanner·성능 측정·작성자 외 리뷰는 미실행입니다.
`make security`의 안내 출력을 scan 성공으로 기록하지 않습니다.

## 남은 C 개발과 연결 조건

| 작업 | 남은 개발·확인 | 필요한 선행 작업 |
| --- | --- | --- |
| W4-C2 | Proof 폐기 API, 현재 lifecycle 연결·RPC 보류·재검증 | 하민님 W4-B3 Reader/Writer·receipt |
| W4-C3 | 수신자 binding 대조, consume Operation·권한·경쟁 요청·최종 체인 상태 | 하민님 W4-B2/B3 |
| W5-C1 후속 | 신규 폐기·consume 경로를 권한표·CSRF·입력·요청 ID 충돌 전수 검사에 추가 | W4-C2/C3; 하민님 W4-B2/B3 |
| W5-C2 | Operation/감사·DB/체인 차이·재시도·복구/stale 공통 응답 연결 | 하민님 W5-B1/B2; 기존 DB/API 부분은 독립 개발 가능 |
| W5-C3 | Compose·준비 상태·계정/migration/seed·실제 기동 안내 | 하민님 배포 정보; 최종 웹 흐름은 형준님 A 연결 |
| W6-C1 | 발행/등록/consume 동시 요청·프로세스 종료·DB/체인 복구 | W5-C1/C2, 하민님 W6-B1; consume은 W4-C3 |
| W6-C2 후속 | 신규 폐기·consume API 보안, Contract 우회 호출 경계·독립 리뷰 | W4-C2/C3, 하민님 W6-B3, 인준님 독립 확인 |
| W6-C3 | DB/서명기 백업·보존 복구·migration 호환·버전 복귀·체인 재배포 대응 | W5-C3, 하민님 W6-B2; DB/API 자체 부분은 독립 개발 가능 |
| W7-C1~C3 | 동결 후 결함 수정, 시연 계정/데이터 패키지, 후보 SHA·RC 확정 | W6-D3와 해당 W5/W6 작업·팀 전체 검사 |

이번 요청에서 W5-C2/C3·W6-C1/C3·W7 작업은 구현하지 않았습니다.
형준님은 오류/권한 안내의 실제 화면 연결, 인준님은 독립 실패·브라우저/다른 환경 재현을 확인합니다.
하민님 Contract/Adapter/indexer 구현을 대신 수정하지 않았습니다. 단계 전체 완료와 PR 리뷰·병합은 별도입니다.
