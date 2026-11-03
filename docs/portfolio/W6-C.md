# W6 C — 실제 복구·보존 재현·API 보안

**현재(2026-10-16): 5.1 신규 지갑 C 독립 복구·검증을 추가했으며, 실제 B/A/D 연결·외부 리뷰·팀 단계 완료는 대기입니다.**

아래 초기 기록은 2026-10-01 상태이며 최신 결과는 마지막 절입니다.

C / @Jordi2801K, W6-C2. 2026-10-01, 선행 W5-C1 `b6d7d67`,
branch `feat/w6-c-security-checks`, 검증 코드 `9100ca9`.
기존 API 독립 구현·검사 완료이며 신규 W4-C2/C3 연결 검사·단계 전체 완료는 대기입니다.
phase/W6가 아직 없어 자기 W5 준비 branch 위에 작업을 쌓았으며 단계 생성 후 재정렬합니다.

기존 세션·PBKDF2·파일 서명기를 재사용해 cookie 형식·실제 HTTPS Secure,
비ASCII CSRF 거부·미등록 계정 dummy 계산·SQL 오류 bind 숨김·directory descriptor 파일 접근을 보완했습니다.
0700/0600·UID·symlink/hard link/FIFO·challenge·directory 교체 경합을 검사했습니다.
새 dependency·migration·Contract/Adapter 변경은 없습니다. Codex가 구현·검사·문서화를 보조했습니다.

Python 3.13/macOS, 실제 HTTP ASGI·SQLite·임시 파일·합성 Adapter 범위:
전체 `python -m pytest -q` 228 passed / opt-in 4 skipped.
W5 31개·W6 18개 보안 사례를 포함하며 Ruff 전체·compileall·diff·OpenAPI 원본 일치 검사 통과.
최종 코드 변경 후 전체 검사를 수행했고 SQL 오류 문자열의 비밀값 숨김을 확인했습니다.
신규 성능 수치나 완전한 로그인 timing 동일성은 측정/주장하지 않습니다.

검사 범위·명령·잔여 W4~W7 C 작업은 [보안·잔여 개발 보고](../api/w6_c_security_report.md)에 기록했습니다.
실제 PostgreSQL/Anvil·브라우저·다른 환경·외부 보안 scan·작성자 외 리뷰는 미실행입니다.
폐기/consume 신규 API 검사는 W4-C2/C3 이후, Contract 직접 호출 우회 검사는 하민님 W6-B3와
인준님 독립 확인이 필요합니다. W6-C1/C3은 이번 범위가 아닙니다.
메모리 요청 제한은 로컬 단일 worker 전용이며 재시작 초기화·프록시 예산 공유 한계가 남습니다.


## 2026-10-03 C1~C3 통합 결과

C / @Jordi2801K. 병합된 W4 `8011f7f` → W5 #37 → W6 #38 준비 branch입니다.
검증 코드 `e3fced2` (병합 정리 `db2955e`는 코드 차이 없음); 문서 최종 SHA는 PR head로 구분합니다.

| ID | 실제 구현·검증 | 재사용·협업 |
| --- | --- | --- |
| W6-C1 | 실제 API 재시작, 제출 응답 유실 UNKNOWN, consume 제출 후 SIGKILL, 동일 hash/nonce 복구, 동시 발행·consume, RPC 보류 | C W4 DB/advisory lock + B Writer P1 `65b041e`; B 소유 소스 수정 없음 |
| W6-C2 | W4 신규 경로 포함 인증/기관/CSRF/binding/재시도 회귀, signer/seed credential dir_fd·FIFO 보호, FastAPI/Starlette/pytest 패치·공유 lock·감사 명령 | 초기 C 보안 #38 재사용; analyzer FastAPI 제한만 함께 조정, D 호환 리뷰 대기 |
| W6-C3 | 실제 pg_dump→새 빈 DB pg_restore, 서명기 보존·공개 signer 일치, migration 0006→0005→head, 계정/Proof/세션/idempotency 보존, 새 deployment 거부 | 기존 Alembic·PostgreSQL 도구·B deployment identity를 재사용; 복원 runbook 제공 |

### 실행 근거

- 전체 Python: **302 passed, 6 skipped**. 기존 live gate 4 + opt-in C live 2는 기본 실행에서 제외됩니다.
- C live `make test-w6-c-live`: **2 passed**, 실제 PostgreSQL 16.4/Anvil/별도 uvicorn process.
- Indexer/Writer 회귀: **122 passed, 2 skipped**; Foundry 1.4.4 계약: **22 passed**.
- PyPA `make security`: 잠금 패키지 **50개, 알려진 취약점 0건**. [원본 결과](../qa/w6-c-python-audit.json).
- 기존 웹: lint/typecheck/build 통과, **8 tests passed**. A 최신 공식 웹 PR #44 전체 연결 검증은 아닙니다.
- 격리 Compose 새 볼륨·무작위 loopback port의 6개 서비스 기동, API ready/analyzer live/web HTTP 200.
  migration·legacy seed·배포·P0 계정 준비 및 실제 카드 VERIFIED+ACTIVE / TAMPERED+AMOUNT_MISMATCH 통과.
- Ruff/compileall/diff 및 전체 모델 생성 통과. v1/v2 Golden fixture는 변경되지 않았습니다.
- 환경: macOS/Python 3.13.0, 컨테이너 Python 3.13.7; 합성 데이터만 사용했습니다.

### 실패 분석·선택

- 기존 legacy seed 기관 ID와 본선 신청 ID가 겹쳐 activation이 실패했습니다. .env 본선 기관 ID를
  분리하고 기존 username/기관 충돌은 덮어쓰지 않고 거부했습니다.
- restore 후 같은 request ID의 body를 새 만료 시각으로 만들면 충돌했습니다. 원래 body를 재사용해
  정상 idempotency 거부와 복원 성공을 구분했습니다.
- live deployment output도 공유하면 실행 중 Compose의 manifest와 충돌합니다. 포트/DB뿐 아니라
  배포 출력·ABI·manifest를 임시 checkout으로 격리했습니다. 공유 B 파일을 수정하지 않았습니다.
- 구 storage smoke의 고정 port/미연결 가정을 실행 환경 변수로 명시해 실제 연결 검사에 재사용했습니다.
- sandbox의 macOS 시스템 설정 접근으로 uv/forge가 종료되어 같은 검사를 허용된 환경에서 재실행했습니다.
- `.env` 덮어쓰기 가능성은 자동 승인 검토가 거부했습니다. 새 작업 공간에 파일이 없음을 확인하고
  exclusive create로 기존 설정 보존을 보장했습니다. 미해결 승인 차단은 없습니다.
- Starlette httpx TestClient deprecation과 기존 웹 CSS 경고는 실패가 아닙니다. 새 httpx2는 추가하지 않았습니다.

### 한계·인계

상세 절차: [W6 복구·보안 runbook](../api/w6_c_recovery_runbook.md).
공유 runtime/CI/lock/문서 조율은 C; B projection/Writer, A UI 응답 소비, D analyzer 호환/독립 재현 리뷰가 필요합니다.
CI에 보안 감사·실제 C 복구 job을 추가했습니다. Codex가 구현·검사·문서화를 수행했고 사람의 별도
코드 리뷰를 받은 것으로 표시하지 않습니다. phase/W5·W6 생성/재정렬·리뷰 후 병합과 A/D 팀 전체
흐름·다른 노트북 확인은 남습니다. 운영 배포/실제 사용자 DB 복원/무료·유료 외부 provider 호출은 하지 않았습니다.

## 2026-10-16 — 5.1 신규 지갑 C 후속

C / @Jordi2801K, V5-W6-C. 시작 기준은 #62 `eaa0d16`, 작업 branch는 `feat/v5-w6-c-recovery-integration`, 최종 검증 코드 SHA는 `b3c10a5e4d0358b7d0754260283853b0338e072f`입니다. 복구/CLI 구현은 `c17a8f5`, 후속 코드는 검사 import 보완입니다. [Draft PR #63](https://github.com/OriginProof-3web/OriginProof/pull/63)을 생성·공유했습니다. 위 2026-10-03 결과는 구 Registry 경로의 과거 기록으로 유지합니다.

기존 W1~W5에는 신규 지갑 API의 실제 프로세스 종료·복원 근거와 API 밖 검증 명령이 없었습니다. 기존 C 복구 helper와 API factory·검증 코어·공유 ABI를 재사용해 전용 PostgreSQL/HTTP 프로세스 검사와 직접 RPC CLI를 추가했습니다. 새 서비스·의존성·migration은 만들지 않았습니다. B Registry와 D 분석기는 아직 없다는 사용자 확인에 따라 테스트용 합성 증거만 주입했고 생산 Adapter/분석기는 구현하지 않았습니다.

| 작업 | 실제 결과·개인/재사용 경계 | 근거 |
| --- | --- | --- |
| 백업·복원/원본 보존 | 실제 pg_dump→빈 DB pg_restore, 버전 1/2 원본·기관 서명·보고서/원본 동의·로그인·구 저장 행 유지 | 신규 live 5개 중 복원 사례 |
| 프로세스/동시성·보안 | 실제 SIGKILL·UNKNOWN 재조회/전송 1회·확정 저장 실패 복구·RUNNING/QUEUED·삭제 후 늦은 종료·다른 계정의 같은 다음 버전 202/409·CSRF/권한/크기 | [실행 가능한 검사](../../scripts/ci/test_v5_c_recovery.py) |
| 독립 검증 도구 | C 순수 검증 코어 + 공유 ABI의 직접 RPC 해독. 로컬 비교·신뢰 domain·고정 block/과거 키·누락 증거를 처리 | [CLI](../../scripts/verify_wallet_document.py), [33개 검사](../../scripts/ci/test_wallet_independent_verifier.py) |
| 실행/연결 인계 | Makefile·기존 recovery CI에 신규 검사 추가, 백업/복원·B/A/D 연결·후보 동일성 절차 | [5.1 runbook](../api/v5_c_recovery_runbook.md), [검증 SHA/환경/결과 원본](../handoffs/v5_c_implementation.md) |

실제 신규 live **5 PASS**, 기존 PostgreSQL/Anvil 복구 **2 PASS**, 전체 Python **527 PASS / 14 SKIP / 기존 warning 1**입니다. 새 frozen/offline archive 환경에서도 전체 **527 PASS / 14 SKIP**를 재현했습니다. 100회 일반 검증의 로컬 p50/p95를 기록했지만 합성 Registry이며 성능 향상이나 실제 체인/모델 목표 달성을 주장하지 않습니다.

늦은 분석 결과 검사에서 단순 상태 조회만으로는 worker의 최종 저장 시도 완료를 증명하지 못했습니다. 테스트 processor의 task 완료 marker를 기다린 뒤 DB를 확인하도록 보완해 CANCELLED/보고서 없음이 유지되는지 검사했습니다. production 동작을 테스트 편의에 맞춰 바꾸지 않았습니다. 독립 CLI는 누락 metadata·RPC/ABI 장애를 성공으로 대체하지 않고 INCONCLUSIVE로 반환하며 VERIFIED와 현재 상태/경고도 분리합니다.

첫 원격 CI의 c-recovery/Contract는 통과했으나 새 검사 import가 `python -m pytest`의 cwd 경로에 의존해 python-quality가 수집 단계에서 실패했습니다. CI와 같은 `pytest` 실행으로 로컬 재현한 뒤 `importlib.util` 파일 로딩으로 보완했습니다. 수정 코드의 새 frozen/offline 사본에서도 직접 `pytest`로 전체 통과를 재현했으며 실패/재검사 근거는 위 구현 기록에 보존합니다.

사용자님은 잔여 C 개발과 팀원 신규 구현 부재를 확인해 주셨습니다. Codex가 기존 흐름 조사·구현·검사·문서화를 수행했으며 사람이 코드를 별도 리뷰한 것으로 기록하지 않습니다. 작성자 외 기여/코드 확인은 미확인입니다. 실제 B Adapter/배포/G07, A 지갑/화면, D 모델/독립·다른 PC 재현, 동일 RC 리허설은 남아 있습니다. C의 독립 준비 결과이며 단계 전체 완료가 아닙니다.

## 2026-10-18 셀프 리뷰 수정·복구 재검증

사용자님 요청으로 W3~W5의 만료·request ID 예약·합성 상태 수정이 반영됐습니다.
검증 코드 `ac9109b`의 C 전용 전체 Python은 620 PASS / 15 opt-in SKIP / 기존 경고1입니다.
누적 후보 #77 검증 코드 `ff7dd6c2be94959c9a9f8392dcd2e2edaa98a837`에서는 전체 Python
629 PASS / 15 SKIP, D 명시 QA 62 PASS 및 기존+신규 실제 복구 8 PASS를 확인했습니다.
복구 검사는 임시 PostgreSQL·실제 API 프로세스에서 동시 동일 alias 재시도, pg_dump/restore
뒤 같은 Operation 재조회·본문 변경 409를 포함합니다. 합성 체인 helper 두 곳의 REVOKED
보존도 맞췄으며 API/계약 생성물 변경은 없습니다. 기존 실제 복구 2개는 Anvil을 사용하지만
신규 6개의 Registry/분석기는 합성입니다. Codex 자체 검사이며 팀원의 독립 리뷰는 별도입니다.

## 2026-10-18 확대 감사 후 앞의 두 묶음 수정

사용자님 지시로 공동승인·키 증명과 Operation·복구의 7개 지적을 C 누적 작업본에 반영했습니다.
기준은 `feat/v5-w6-c-recovery-integration`의 `8f2a0714c928a7b4954ff8897ea47304ca1233af`이며,
이 기록은 후속 수정 작업본의 검사 결과입니다. 앞 단계 PR과 #77 전파는 별도 후속 묶음입니다.

기존 계정 잠금 아래 KeyProof request ID를 다른 challenge와도 비교하고, 0 keyId·현재 signer와
같은 주소의 교체를 proof 소비 전에 거부했습니다. 기존 저장 필드를 사용해 migration이나 새
의존성은 추가하지 않았습니다. 과거 종료 signer의 API 사전 조회는 B의 실제 이력 경계 연결이
필요하며, 현재 주소 비교만으로 전체 과거 주소를 검증했다고 주장하지 않습니다.

직접 거래는 RPC 전후에 서명 요청 → Operation 순서로 잠그고 최신 행·확정 상태·해시 binding을
다시 검사합니다. 이 순서는 동시 직접 접수와 발행 원본 FK 저장의 잠금 순서도 맞춥니다.
중단 전 lookup 해시를 먼저 재조회하고, 불일치하는 미검증 후보는 검색으로 복구합니다.
작업 만료 조건은 조회·재요청·복구·v1 목록·감사·물리 정리에 공유하며 만료 목록은 pagination
전에 거릅니다. 기존 작업의 복구 안내와 신규 wallet 작업의 RECONCILE/RESIGN은 각각 유지합니다.

검사는 C 전체 Python **647 PASS / 16 opt-in SKIP / 기존 경고 1**, 새 HTTP 경계 회귀 **27개**를
포함합니다. 실제 PostgreSQL·별도 API 프로세스에서 성공/실패 거래의 응답 순서를 제어한 검사
**1 PASS**, 실제 DB의 기존·미해결 Operation/감사 보존 검사 **1 PASS**도 확인했습니다.
Registry/receipt는 합성입니다. Codex가 수정·검사를 수행했으며 사람의 독립 리뷰는 미확인입니다.
소유 Python 경로의 Ruff와 변경 API/검사의 compileall도 통과했습니다. 광역 lint가 스캔한
vendored Foundry Python의 기존 지적 26개는 수정하지 않았습니다.

앞의 두 묶음 작업 시점에는 기존 선택 PostgreSQL 검사 설정과 PR 전파를 남겼습니다.

## 2026-10-18 후속 실제 DB 검사와 PR 전파

기존 선택 PostgreSQL 검사의 fixture에 합성 이메일 secret을 명시했습니다. 외부 secret을
제거하고 빈 임시 PostgreSQL에 Alembic head를 적용한 뒤 원래 검사 1 PASS를 확인했습니다.
앞선 재현 harness가 metadata만 생성해 준비 상태에서 실패했던 것과 구분합니다.
운영 HMAC·readiness 검사를 완화하지 않았습니다.

W2→W3→W4→W5→W6 순서로 수정 이력을 전파했습니다. 단계별 전체 Python은 각각
512/557/565/598/647 PASS이며 skip은 8/8/8/9/16개입니다. C 누적 검증 소스는
`26b8975`와 동일하며 선행 PR 병합 뒤에는 기여 문서만 추가됐습니다.
통합 후보 검증 소스 `2a25ef73482e01d54858c3745dd7f59722270235`에서는 전체 Python
656 PASS / 16 SKIP, D 명시 QA 62 PASS, Foundry 101 PASS, 실제 복구 9 PASS를 확인했습니다.
기존 실제 복구 2개는 PostgreSQL/Anvil, 신규 7개는 PostgreSQL/API 프로세스와 합성 Registry입니다.
생성물 재생성 diff 없음·자체 Python Ruff·diff 검사를 통과했습니다.
원격 공유 뒤 정확한 head CI를 별도로 확인하며, 사람의 재리뷰·실제 A/B/D 연결·G07은 별도입니다.

## 2026-10-18 수정 후 셀프 리뷰 P2 두 건

이전 배포의 미해결 Operation이 새 배포의 같은 업무 nonce를 예약하던 문제를 고쳤습니다.
예약 비교에 Operation이 저장한 domain(chainId·Registry 주소)을 포함하며, 같은 배포의 중복
nonce는 계속 409이고 이전 배포 작업은 그대로 보존합니다. 동시 직접 접수 뒤 정식 거래가 연결된
상태에서 거부된 lookup 후보 때문에 첫 reconcile이 409를 반환하던 문제도 고쳤습니다.
정식 해시가 있으면 그 해시만 조회하고, 서로 다른 해시의 재연결 거부는 유지합니다.

수정은 #60에서 시작해 #61→#62→#63→#77로 merge했습니다. 회귀 3개(주소 변경·chain ID 변경·
잔여 lookup 후보)는 수정 전 409로 실패하고 수정 후 통과합니다. 단계별 전체 Python은
W3/W4/W5/W6/후보 560/568/601/650/659 PASS입니다. 임시 PostgreSQL 16.4의 동시 접수 반례 2개,
실제 PostgreSQL·API 프로세스 복구 7개, 정식 migration 적용 DB 선택 검사 1개가 통과했고,
migration head의 `alembic check`와 0006 downgrade 뒤 재적용도 차이가 없었습니다.
Registry/receipt는 합성입니다. Claude가 수정·검사를 수행했으며 사람의 재리뷰는 미확인입니다.

## 2026-10-27 분석기 생산 연결 (블록 8·10)

`PhishingAnalyzer`(D #75~#101)를 생산 `app`의 `analysis_processor`로 연결했습니다. 공급자는 기존 `LLM_PROVIDER` 설정을 그대로 쓰고, 기본값 mock은 규칙 근거만 돌려줍니다. `create_app()`의 기본값(None)은 그대로라 검사·fixture는 계속 명시적으로 주입합니다. 연결을 위해 API에 analyzer workspace 의존성을 추가했고(`uv.lock` 2줄, 버전 변경 없음), `api.Dockerfile`에 analyzer 소스 복사를 넣었습니다. 텍스트 입력은 migration 순서 문제로 기본값 false를 유지하고, runbook에 켜는 절차를 적었습니다.

AI(Codex, claude-opus-5-5)가 사용자님 지시로 구현·검사·기록했습니다. D 리뷰(analyzer 의존 방향·lock)는 PR에서 요청합니다.

## 2026-10-27 문서 사진 입력 계약 (블록 11)

`/v3/inputs`가 `DOCUMENT_IMAGE`를 받습니다(기본 꺼짐). 형식 검사는 D `SemanticInput`을, 판독은 D `document_image_to_text`를, 판독문 분석과 위치 대조는 D `analyze_conversion`과 C `ground_report`를 재사용했습니다. 새 요청 모델은 `originproof_core/wallet_inputs.py`에 두었습니다. 처음에는 `wallet_contract.py`에 넣었는데, #100의 동결 평가 후보가 그 파일의 sha256을 고정하고 있어 D 검사가 실패했고, 그래서 파일을 분리했습니다(평가 기록은 건드리지 않음). 이미지가 켜졌을 때만 `/v3/inputs` 본문 상한을 늘립니다. 근거 위치는 판독문 글자 기준이며 픽셀 영역과 판독문 전체 표시는 후속입니다.

AI(Codex, claude-opus-5-5)가 사용자님 지시로 구현·검사·기록했습니다.

## 2026-10-27 Track B 원본 찾기 (#88)

검증 코드가 없는 문자에서 읽은 기관·금액·계좌(또는 공문 번호)로 보관 중인 발행 기록을 찾는 `POST /v3/document-lookups`를 추가했습니다. 일치하는 기록이 없으면 `UNVERIFIED`, 여럿이면 `AMBIGUOUS`이고, 하나면 기존 검증 흐름을 `run_verification`으로 떼어 내 그대로 실행합니다. 부분 일치를 VERIFIED로 올리지 않습니다. v5 content에 수신자 정보가 없어 수신자 해시 키는 넣지 않았고, 발송일 범위와 분석기 자동 추출 연결은 후속입니다.

AI(Codex, claude-opus-5-5)가 사용자님 지시로 구현·검사·기록했습니다.

## 2026-10-27 합성 회원가입 (블록 14)

`POST /v1/auth/register`를 추가했습니다(`API_SIGNUP_ENABLED`, 기본 꺼짐). 개인 회원은 `recipient`, 기관 회원은 합성 명부의 기관 ID를 가진 `issuer`로 만들어 기존 기관 신청 흐름을 그대로 탑니다. 실제 개인정보를 받지 않도록 예약 도메인 `.invalid`(기관은 명부 도메인)만 허용했습니다. 비밀번호는 기존 PBKDF2 해시와 로그인 요청 제한을 재사용합니다. 계획에 있던 약관 동의 기록 저장(migration)과 탈퇴 API는 합성 도메인 한정이라 생략했습니다.

AI(Codex, claude-opus-5-5)가 사용자님 지시로 구현·검사·기록했습니다.

## 2026-10-31 기관 가입 차단 (B-01)

기관 회원 가입이 메일 도메인만 보고 승인 없이 `issuer` 권한을 주던 결함을 막았습니다. 메일 소유 확인이 없어 외부인이 기관 직원 권한으로 발행과 키 폐기까지 할 수 있었습니다. `kind: "business"`는 이제 403 `BUSINESS_SIGNUP_DISABLED`이고 계정을 만들지 않습니다. 기관 계정은 운영자가 발급합니다. '가입 후 승인 전까지 권한 없음' 방식은 기관 신청 흐름과 함께 새로 설계해야 해서 넣지 않았습니다.

AI(claude-opus-5-5)가 사용자님 지시로 구현·검사·기록했습니다.
