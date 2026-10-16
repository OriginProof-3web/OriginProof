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
