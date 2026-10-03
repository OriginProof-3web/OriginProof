# W4 D — 독립 상태·1회 사용 검사

- 담당 D / 여인준님 `@yijun0330`, 착수일 2026-10-03.
- 작업 ID W4-D1/D2; W4-D3 브라우저는 A 연결 후 별도 확인.
- 후속 D3 실행 절차·합성 계정/입력·DB/체인 snapshot 준비: [D3 브라우저 준비](w4-d3-browser.md).
- 기준 `phase/W4@8011f7fe3da033c9253894a9de0fd98aa7bbcc16`, 작업 `test/w4-d-lifecycle-qa`.
- 작업 PR [#49](https://github.com/OriginProof-3web/OriginProof/pull/49), C 작성자 외 리뷰 요청.
- C #36/#42가 병합된 제품과 B의 Contract/Reader/Writer를 재사용합니다.
- 원래 unborn mvp/ai와 W3 개인 PR/설정은 보존합니다. 앱 worktree 생성은 Git unavailable로
  실패해 새 임시 clone을 사용합니다. A/B/C 제품 코드·lockfile·Golden을 수정하지 않습니다.

## 계획과 완료 기준

| 작업 | 사례 | 검사 계층·완료 기준 |
| --- | --- | --- |
| W4-D1 | 만료 직전/정각/직후, 정상 교체, 과거 키 기간 종료, 유출 폐기, 기관 중지/복귀 | 두 유형의 signature/verification과 현재 lifecycle을 구분. 승인 ADR 유지 |
| W4-D2 | 권한·CSRF·actor 주입, 문서 consume, 서로 다른 주체의 경쟁, 재시도·재사용, 직접 계약 우회, 반복 조회·폐기 | 한 consume event, 같은 요청은 같은 tx, 실패 receipt는 상태를 바꾸지 않음 |
| W4-D3 | 키 교체→발행→폐기→재검증, 허가 사용→재사용 거부의 새 브라우저 세션 | A W4 화면 연결 후 실제 E2E. 현재 미실행 |

## 실행 방식

`fixtures/finals/w4_cases.json`은 C의 공개 합성 Golden을 재사용하는 코어 기대값입니다.
라이브 검사는 자동 생성한 새 Docker 네트워크·tmpfs PostgreSQL·Anvil만 사용하고 종료 시
그 자원만 정리합니다. 개인 DB/RPC 주소는 인자로 받지 않습니다. API 요청은 ASGI transport,
DB·서명·Reader·Writer·Contract·receipt·event는 실제입니다. socket HTTP/브라우저 통과로
표현하지 않습니다. API의 신뢰 시각만 통제하고 만료 검사 때 실제 EVM 시각을 같이 진행합니다.

```sh
UV_PROJECT_ENVIRONMENT=.uv-venv uv sync --frozen --all-packages --all-groups
PYTHONPATH=apps/api/src:packages/python:services/analyzer/src \
  .uv-venv/bin/python -m pytest -q fixtures/finals/test_w4_lifecycle_qa.py
docker build -f infra/docker/deployer.Dockerfile \
  --label org.opencontainers.image.revision=8011f7fe3da033c9253894a9de0fd98aa7bbcc16 \
  -t originproof-w4-d-qa-deployer:8011f7f .
W4_LIVE_QA=1 W4_QA_DISPOSABLE=1 \
  PYTHONPATH=apps/api/src:packages/python:services/analyzer/src \
  .uv-venv/bin/python -m pytest -q fixtures/finals/test_w4_lifecycle_qa.py
```

위 image는 명시된 phase 제품 코드로 빌드해야 합니다. 새 API·Contract 변경 시 기준 label과
검증 결과를 함께 갱신합니다. 호스트 forge, 운영 배포, 보존 DB reset, 유료 AI는 필요하지 않습니다.

## 실행 결과

- 검사 코드 SHA: `0bb5da42d64b9ce298cb2de2951b327da6bc4fc7`.
- Node 22.18.0, pnpm 11.19.0, Python 3.13.7, uv 0.8.17, PostgreSQL 16.4,
  pinned Foundry 1.4.4. [환경 fingerprint](w4-d-environment.json).
- 새 uv 환경을 현재 frozen lockfile로 설치했습니다. 웹 의존성은 byte가 같은 lockfile의
  W3 설치를 재사용했고 명령별 임시 npm/uv cache를 사용했습니다. 개인 설정은 유지했습니다.

| 실제 명령·검사 | 결과 | 계층·한계 |
| --- | --- | --- |
| 위 W4 fixture opt-in pytest | **21 passed / 0 skipped / 12.02초** | 코어 20 + 순차 실제 PG/Anvil API 검사 1. ASGI transport |
| 고정 코드의 새 archive 재현 | **21 passed / 0 skipped / 12.04초** | 새 DB/Anvil 배포·migration·계정·서명기 준비부터 반복. 기존 locked Python 설치·동일 제품 deployer image 재사용 |
| `make bootstrap-check` | 통과 | 구조·환경. 새 clone .env는 mock/gpt-6-luna 두 기본값만 작성 |
| `make test` | **248 passed / 4 skipped** | 기존 actual opt-in 미설정. 새 D fixture는 기본 testpaths 밖이라 별도 실행 |
| `uv run pytest -q services/indexer/tests` | **86 passed / 1 skipped** | 기존 live chain opt-in 미설정, 위 D 실제 상태 검사와 구분 |
| `make test-contracts` | **22 passed / 0 skipped** | 공식 Foundry 컨테이너, fuzz 512회. 호스트 forge 미설치 |
| `make lint`·`make typecheck`·`make env-fingerprint` | 통과 | 웹 ESLint/tsc·Ruff·Python compileall. 정적 Python 타입 검사로 표현하지 않음 |
| 새 fixture Ruff·JSON·문서 링크·diff | 통과 | A/B/C 제품·lockfile·Golden 변경 없음 |

반복 실행 건수는 합산하지 않습니다. 코어의 consumed 사례는 요청형에만 적용하며 문서형의
실제 consume은 거부를 검사합니다. 이미지·모델·OCR 정확도와 성능 개선 수치는 측정하지 않았습니다.

## 실제 W4-D1/D2 증거

1. 새 두 기관을 실제 API로 신청·승인·체인 활성화하고 보호된 발행키를 등록했습니다.
   두 유형을 실제 ECDSA 서명·DB 저장·ProofStatusRegistry 등록 후 VERIFIED + ACTIVE로 확인했습니다.
2. 익명·운영자·다른 기관·다른 수신자 consume 거부, CSRF 거부, actor_kind/binding/account_id
   주입 422, 문서형 consume 409. 반복 읽기/거부 뒤 Operation·Audit 건수와 consume event 불변.
3. 실제 Registry 관리자 주소의 직접 consume과 gateway의 잘못된 recipient binding을
   EVM에 제출했습니다. 두 receipt status=0, 소비 event 없음·Proof ACTIVE 유지.
4. 발행자/지정 수신자의 다른 요청 ID 경쟁: HTTP 200 1개·409 1개, consume event 1개.
   같은 요청 재시도는 같은 Operation/tx, 새 ID 재사용은 REPLAY_DETECTED. 다른 Proof에 같은
   요청 ID를 재사용하면 REQUEST_ID_CONFLICT. 같은 요청 ID의 병렬 2건도 동일 Operation/tx/event 1개.
5. 소비한 요청형을 적법하게 폐기한 뒤 PROOF_REVOKED와 REPLAY_DETECTED 모두 보존,
   consumedAt/revokedAt 존재. 반복 폐기는 no_change·추가 tx/event 없음. 문서형도 실제 폐기 반영.
6. 두 유형 정상 키 교체: 새 발행은 새 selected key, 이전 Proof는 ACTIVE 유지.
   과거 키 기간 종료 뒤에도 발행 당시 유효했던 서명은 VERIFIED + ACTIVE입니다.
   유출 폐기는 두 유형의 과거 Proof를 VERIFIED + ISSUER_KEY_REVOKED로 사용 불가 처리합니다.
7. Office 중지→VERIFIED + ISSUER_SUSPENDED, 실제 복귀→ACTIVE. 정상 서명과 현재 상태를 구분합니다.
8. 이번 실행의 Anvil만 중지하면 검증은 INCONCLUSIVE/null/DEPENDENCY_UNAVAILABLE,
   consume은 503, Operation/Audit 불변입니다. 상태를 보존한 재시작 후 기존 Proof가 다시 ACTIVE입니다.
9. API 신뢰 시각과 실제 블록 시각을 같은 초로 맞춰 만료 -1/0/+1초를 확인했습니다.
   직전은 ACTIVE, 정각/직후는 VERIFIED + EXPIRED이며 consume 거부. 체인의 consumable_at도
   요청형만 직전 true, 만료 후 false입니다. 문서형은 항상 false입니다.

## 실패·원인·수정

- RPC 복구 추가 검사 첫 실행은 임시 Anvil 재시작 후 endpoint에 연결되지 않아 실패했습니다.
  독립 probe로 Docker의 `127.0.0.1::8545`가 stop/start 때 다른 임의 호스트 포트를 받는 것을
  확인했습니다. 새 자원에만 빈 loopback 포트를 명시하여 재시작 주소를 유지했고 최종/새 archive
  전체 검사가 통과했습니다. 성공을 만들기 위해 Reader·Writer·Contract를 바꾸거나 skip하지 않았습니다.
- 별도 indexer 검사 첫 명령은 기본 uv cache 접근 제한으로 중단했습니다. 기존 task cache를
  해당 명령에 지정한 뒤 86 passed/1 skipped로 확인했습니다. 개인 cache 권한/설정은 수정하지 않았습니다.
- 기본 회귀의 Starlette/anyio deprecation warning 1건은 남아 있습니다. 의존성 보안 audit은
  이번에 실행하지 않았으며 W3에서 기록한 취약점이나 다른 branch audit의 해결을 주장하지 않습니다.

## 완료 범위와 다음 담당자

- D W4-D1/D2의 위 독립 사례·실행/재현 증거는 준비됐습니다. 사람 리뷰·phase 반영은 별도입니다.
- A W4-A1/A2/A3 화면이 이 phase에서 연결되지 않아 **W4-D3 전체 브라우저 E2E는 미실행**입니다.
  API의 키 교체/폐기/consume 성공을 웹 완료로 표시하지 않습니다.
- A 연결 후 새 세션에서 키 교체→새 발행→폐기→재검증, 지정 수신자 사용→재사용 거부,
  문서형 사용 버튼 제한·RPC 보류 표시와 실제 체인 재조회를 확인해야 합니다.
- C: 작성자 외 QA 리뷰와 필요한 병합, A API 인계·통합 SHA 조율. B: 실제 소비 경계·계약 리뷰.
- 실제 socket API/브라우저, 전체 Compose smoke, indexer 프로세스 재시작, 다른 컴퓨터 재현,
  유료 모델·운영 배포는 미실행입니다. 이 PR은 W4 전체 완료·integration 승격 PR이 아닙니다.
- pytest fixture가 각 실행에서 만든 PostgreSQL·Anvil·네트워크를 종료/제거했습니다.
  Foundry 검사의 별도 task 네트워크도 정리했고 보존 DB/서비스/작업 파일은 유지했습니다.
