# W2-D1 후속 — 장애·실제 프로세스 재시작 검증

- 담당: D / 여인준님 `@yijun0330`, 2026-10-02
- 시작 기준: `phase/W2@812265b285b218e004a08b632ac3aa36125add21`
- 작업 branch: `test/w2-d-recovery-qa`
- 후속 PR: [#45](https://github.com/OriginProof-3web/OriginProof/pull/45), `phase/W2` 대상 초안. C 리뷰 요청 완료.
- 최종 실환경 검사 코드 SHA: `dd5fc7479b71610be7d53ebbcd94a4b7f8d19342`
- [환경 fingerprint](w2-d-recovery-environment.json): Python 3.13.7, Node 22.18.0,
  uv 0.8.17, Docker 29.7.2, Compose 5.5.1. host forge 미설치는 차단 조건이 아닙니다.
- 새 QA 도구: [test_w2_recovery_qa.py](../../scripts/ci/test_w2_recovery_qa.py)
- 공유 `scripts/ci`의 작성 담당은 D, 지정 리뷰어는 C입니다. 이번 후속 코드는 리뷰 대기입니다.

## 실제 확인 결과

새 검사는 ASGI 객체 재구성 대신 독립 uvicorn 프로세스를 종료·재기동합니다.
PostgreSQL은 전용 tmpfs 컨테이너, Anvil은 고정 Foundry 컨테이너와 전용 네트워크입니다.
API 세션·Operation·발행키 파일은 이 격리 환경 안에서만 유지합니다.

| 경계 | 기대값과 실제 결과 |
| --- | --- |
| 신청 대기·반려·DB 승인 뒤 체인 반영 전 키 등록 | 모두 409, Operation 0건, 체인 제출 0건. 감사 기록은 승인·반려 결정 2건뿐 |
| 무권한 activation·역할/기관 ID 주입 | issuer의 운영자 요청 403, 허용되지 않은 role/issuer_id 필드 422 |
| 제출 전 RPC 연결 실패 | 실제 루프백 연결을 끊어 503. 체인 제출 없음 |
| 실제 제출 성공 뒤 RPC 응답/hash 유실 | Anvil은 제출을 실행하고 API는 UNKNOWN. DB에 hash 없이 고정 nonce 복구 참조 저장 |
| UNKNOWN 상태의 실제 API 재시작 | PID 변경 후 같은 세션으로 복구. CONFIRMED/receipt/재조회 확인, 제출 횟수 1 유지 |
| receipt 조회 timeout | 실제 HTTP 대기를 Adapter 기본 5초보다 길게 주입. UNKNOWN/DEPENDENCY_UNAVAILABLE과 제출 hash 보존 |
| receipt timeout 뒤 API 재시작 | 저장 hash로 CONFIRMED 복구, reread_block_number 존재, 추가 제출 없음 |
| Anvil 및 API 실제 재시작·새 로그인 | Anvil 자신의 state/history를 dump/load. 기관 ACTIVE, 동일 deployment_id·signer·선택 키 유지. 기존 세션과 새 로그인 모두 재조회 성공 |
| 키 폐기 성공 뒤 클라이언트 HTTP 응답 유실 | 서버의 실제 완료 응답만 버림. 같은 request_id 재시도는 동일 Operation/tx_hash, 추가 제출 없음, 키 REVOKED |

응답 키 객체에 secret_ref/private_key/password/token 필드가 없음을 확인했습니다.
이 검사는 응답 필드 검증이며 전체 로깅·보안 감사 완료를 뜻하지 않습니다.

## B/C 기존 구현 수용 검사

| 실행 | 실제 결과 | 범위 |
| --- | --- | --- |
| 새 opt-in QA 파일 | **3 passed**, 22.86초 | 위 순차 장애 시나리오 1건과 아래 기존 실환경 검사 실행 wrapper 2건 |
| wrapper 안의 기존 `test_live_w1_w2.py`, `test_live_w2_chain.py` | **3 passed** | 실제 PostgreSQL 인증/CSRF/감사/Operation 경계, advisory lock, actual Anvil activation·UNKNOWN nonce 복구·키 회전/폐기·실패 receipt |
| wrapper 안의 `services/indexer/tests/test_live_chain.py` | **1 passed** | Foundry 컨테이너 내부 재배포/manifest, 실제 Adapter 읽기·쓰기, 권한/revert, v1 정상·변조·기관 중지·키 폐기 회귀 |
| `make test` | **171 passed, 6 skipped**, 경고 1개 | API·코어·Analyzer·공유 CI 검사. skip은 기존 opt-in 3건과 새 wrapper/시나리오 3건. 경고는 Starlette/anyio deprecation |
| `pytest -q services/indexer/tests` | **60 passed, 1 skipped** | Writer persistence/receipt/nonce 복구, SQLite event 중복·checkpoint 재개/reorg/재배포 격리. local-EVM skip은 위 컨테이너에서 별도로 실행 |
| `make test-contracts` | **10 passed** | 표준 Foundry 컨테이너. 권한·중복·기간·기관 중지/폐기, fuzz 512회 포함 |
| `make bootstrap-check`, `make lint`, `make typecheck` | 통과 | 구조·환경, Ruff/웹 ESLint, Python compileall/웹 tsc |
| `make env-fingerprint`, `git diff --check` | 통과 | 실제 코드 SHA와 lockfile/컨테이너 설정 해시, 변경 공백 |

Indexer의 checkpoint 검사는 SQLite 저장소 재개 검사입니다. 실제 PostgreSQL Indexer
서비스 프로세스 전체를 재시작한 것으로 확대 해석하지 않습니다. 실제 체인 검사는
위 local-EVM 한 건이며 브라우저 검사는 포함하지 않습니다.

## 같은 SHA에서 재현

저장소 루트에서 Python 3.13·uv·Docker를 준비합니다. 해당 SHA를 checkout하고 lockfile로
의존성을 준비한 뒤 현재 소스의 deployer 이미지를 반드시 새로 빌드합니다.

```sh
UV_PROJECT_ENVIRONMENT=.uv-venv uv sync --all-packages --all-groups --frozen
docker build -f infra/docker/deployer.Dockerfile -t originproof-w2-recovery-deployer .
W2_RECOVERY_QA=1 LLM_PROVIDER=mock OPENAI_MODEL=gpt-6-luna \
PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src \
UV_PROJECT_ENVIRONMENT=.uv-venv uv run --no-sync pytest -q scripts/ci/test_w2_recovery_qa.py
```

QA 도구는 임의 prefix의 전용 DB/Anvil/network를 직접 생성하고 그 환경에만 migration·
합성 계정·로컬 계약 배포를 수행합니다. 기존 DB는 초기화하지 않습니다. 임시 DB 암호는
매 실행 생성되고 개인 .env·계정·키를 사용하지 않습니다. OPENAI_API_KEY는 자식 API 환경에서
제외하며 모델 호출은 하지 않습니다. 종료 시 이 도구가 만든 컨테이너·네트워크만 제거합니다.
임시 pytest 디렉터리에 합성 발행키/state 관련 파일이 남을 수 있으며 Git에 넣지 않습니다.

컨테이너의 기존 B live 검사는 저장소 lockfile과 같은 pytest 8.4.2·pytest-asyncio 0.25.3을
컨테이너에서만 사용합니다. lockfile이나 호스트 전역 패키지를 변경하지 않습니다.

## 실제 실패와 수정

1. 최초 Anvil 재시작 검사에서 이전 호스트 포트로 재접속해 실패했습니다.
   Docker가 동적 published port를 변경했기 때문에 `docker port`를 다시 조회하고
   루프백 RPC relay의 upstream만 갱신했습니다. 제품 설정 변경 없이 재검사 통과했습니다.
2. 기존 B live 검사 실행 시 `uv --package originproof-api --group dev`는 API 패키지에
   dev group이 없어 준비 단계에서 실패했습니다. 루트 lockfile과 같은 pytest 버전을
   임시 컨테이너에 지정해 수집 및 실환경 검사 통과를 확인했습니다.

## 4번 — 리뷰·기여 기록·단계 종료 점검

- PR [#34](https://github.com/OriginProof-3web/OriginProof/pull/34)는 C의
  [실제 승인](https://github.com/OriginProof-3web/OriginProof/pull/34#pullrequestreview-5389403389)
  후 `812265b`로 phase/W2에 병합됐습니다. 승인 대상은 기존 D 문서/CI이며 이번 QA 코드의 승인이 아닙니다.
- [W2-D 기록](../portfolio/W2-D.md)을 갱신했습니다. 현재 W2-B/W2-C 기록은 존재하고
  W2-A 기록은 기준 트리에 없습니다. 다른 담당자의 기여나 본인 확인을 대신 작성하지 않습니다.
- W2-D2 실제 브라우저 신청→승인→키 등록→폐기→새 세션 재조회와 다른 컴퓨터 재현은
  A1/A2 화면 API 연결 뒤 실행해야 합니다. 이번 clean 컨테이너 재현은 그 기준의 대체 증거가 아닙니다.
- 본 후속 PR의 작성자 외 C 리뷰, A 기록/화면 연결 및 전체 W2 검증 뒤 최종 phase SHA를
  결정할 수 있습니다. 현재는 W2 전체 완료나 phase/W2→integration 승격을 수행하지 않습니다.
- 성능 개선율은 측정하지 않았습니다. D의 실제 기여는 QA 구현·실패 원인 분석·실행·기록이며,
  B/C의 제품 구현을 재사용했습니다. Codex가 QA와 기록을 작성했고 사용자님의 API 연결 제외
  지시에 따라 구현 범위를 제한했습니다. 사람의 추가 리뷰는 아직 대기입니다.
