# 5.1 C 후속 구현·재사용 기준

- 작업: V5-W1-C → V5-W2-C → V5-W3-C → V5-W4-C → V5-W5-C, 후속 V5-W6-C 독립 복구·검증.
- 사용자 요청: 재사용 기준 확정, #50 nonce 수정 반영, 공유 계약에 따른 신규 DB/API 개발.
- 기준 integration: `33bc4f4e7456c5ef7c2df8c8bf09f8014e0169f8` (#56 MERGED).
- 재사용 작업본: `ba8946ce1efaeb76946b77064490364a59f0d29e`. 기준 integration을 포함한 C 누적본이며 사용자 변경 없이 시작했습니다.
- 계약: [v5-shared-0.2](../shared_contract_v5.md), [ADR 0004](../adr/0004-v5-governance-wallet-versioning.md). 계약 검토와 실제 체인/웹 연결 완료는 별도입니다.

| 원본 | 채택 범위 | 중복·후속 경계 |
| --- | --- | --- |
| C6 `3ef1fd40943914c1450e8bc05047119ab7eabbc0` | 인증/CSRF/권한·기존 API/DB·Operation·복구·보안/CI·v1/v2 회귀 | 이 작업본의 해당 기능 소스와 동일합니다. #37 `9651062`가 포함돼 있어 다시 복사하지 않습니다. 서버 기관키는 레거시 한정입니다. |
| B #50 `7e75986d68dc7e8b60b4a088f232c8ab26819716` | 제출 전 save_prepared 실패/취소의 nonce 해제·두 회귀 검사 | 새 Writer 전체로 덮지 않습니다. C6의 tx binding/UNKNOWN 보호를 유지합니다. 사용자 요청으로 해당 B 소유 경로의 보완도 수행합니다. |
| B6 `1a7370718a385553c47a0bbae16b7b5639b5f2be` | 기존 Writer/Reader·projection·배포 식별·복구 자산 | C6의 조상입니다. 새 Registry/ABI와의 실제 연결은 B 후속이며 기존 구현을 새 Registry 성공으로 취급하지 않습니다. |
| A5 `56dbd82407e7d04cca97162aebbf276ec6a9f607` | official 웹·QR·오류·접근성의 후속 연결 기준 | A 소스를 이 C API 작업본에 복제하지 않습니다. #54/#48/#53이 포함되므로 별도 전체 반영하지 않습니다. |
| D43 `c16de660914389ba8821612aa3d6c64708085185` | 후보 확인·추출 안전성·provider 경계 참고 | 새 피싱 분석·grounding 완료가 아닙니다. D 분석기를 주입하는 API 경계와 공통 보관/오류를 구현합니다. |
| #56 `b0e0f345fd360e61b98f6e36cf9a57a1bf0d7acd` | wallet 원본 모델·서명·생성물·Golden | 이미 포함돼 있습니다. API /v3와 서명/domain/schema 버전은 별개이며 구자료를 재해석하지 않습니다. |

## 변경 범위와 검사

기존 `apps/`, `packages/`, `scripts/`, `docs/`를 사용합니다. 신규 기관 업무키를 서버에서 생성/보관하지 않으며 체인 확인 불가를 성공으로 대체하지 않습니다. 미선정 입력·Decisions API·공개 배포·기존 DB 삭제는 추가하지 않습니다.

검사는 기존 pytest/Foundry/Node·생성 명령을 재사용합니다. SQLite/ASGI/합성 Adapter 검사와 실제 PostgreSQL·RPC/Registry·브라우저·유료 모델 검사를 구분합니다. 새 DB migration은 기존 자료를 변경하지 않는 추가 테이블 방식으로 준비합니다. 독립 수용 검사·리뷰·실제 연결 근거가 없으면 단계 완료로 판정하지 않습니다.

## 진행 기록

- 재사용 기준: 위 원본·중복·책임 경계를 확정했습니다.
- nonce 보완: #50의 제출 전 예약 해제와 실패/취소 두 회귀를 반영했습니다. 제출 결과 UNKNOWN의 예약 유지도 검사했습니다. Writer+기존 API 회귀 62 PASS, Ruff·diff 검사 통과입니다. 실제 RPC/기관 지갑 연결 검사는 아닙니다.
- DB/API·후속 연결: 해당 구현 커밋과 실행 결과를 아래에 갱신합니다.

### W2 C 독립 구현

합성 명부·데모 메일 코드·지정 내부 승인·키 challenge/서명 증명·공동승인 준비/조회·실제 tx 대조 API와 추가 migration `20261015_0007`을 구현했습니다. 신규 기관 개인키를 생성하거나 단일 운영자로 활성화하지 않습니다. `WalletRegistry` port는 B가 실제 ABI/배포·canonical receipt/event/state 검증 Adapter로 연결하며, 미연결 시 503입니다.

신규 HTTP/SQLite/EIP-712 6개 검사와 기존 회귀를 포함해 454 PASS/6 live SKIP입니다. 임시 PostgreSQL에서 전체 upgrade·schema check·0007→0006→0007 왕복을 통과했습니다. 기존 Alembic 대상에서 빠졌던 projection metadata를 함께 등록해 자동생성이 기존 체인 테이블 삭제를 제안하지 않도록 했습니다. 실제 Registry·브라우저·작성자 외 리뷰는 후속입니다.

### W3 C 독립 구현

초안 원본·EIP-712 검증·기관 서명/Operation의 제출 전 저장, 중계 또는 기관 직접 제출의 tx 대조·UNKNOWN 재조회, 공개 문서·원본/필드/ID 검사와 독립 검증 자료 API를 구현했습니다. 발행은 직접 제출을 기본으로 하며 원본·서명 접수만으로 체인 확정을 표시하지 않습니다. 직접 거래의 request ID 충돌과 잘못된 txHash가 정상 서명 요청을 영구 무효화하지 않는지도 검사합니다.

신규 HTTP 사례 15개를 포함한 해당 API/코어 회귀 65 PASS입니다. 임시 PostgreSQL에서 `0008` upgrade/schema check를 통과했습니다. 원본 bytes·보호 필드·기관 메타데이터/표시명 조작을 분리 검출하고, ID 단독/부분 비교와 RPC 미확인은 INCONCLUSIVE입니다. 새 Registry Adapter는 미연결이며 실제 체인/브라우저 E2E·B/A/D 리뷰는 아직 없습니다.

### W4 C 독립 구현

정확한 latest+1의 초안/제출 검사, 같은 기관의 문서 소유 고정, 버전별 불변 원본, 별도 Revoke EIP-712 요청/제출을 추가했습니다. 기관 정지 중에도 현재 비사고 키의 철회를 허용하고 정상 교체의 과거 서명·현재 사고 경고를 구분합니다. 원자적 버전 전이는 B Registry의 검증된 상태/이벤트를 소비하며 API가 DB의 최신 포인터를 권위로 만들지 않습니다.

신규 HTTP 사례 누적 20 PASS입니다. 다음 버전·과거 대체·최신 철회 후 미복구·동일 nonce 경쟁 거부·타 기관·정지/철회·구키 신규 서명 거부·과거 정상 서명/사고 경고·서로 다른 승인자 1/2/중복 결과를 검사했습니다. 합성 Registry 근거이며 실제 컨트랙트의 원자성·브라우저 연결이나 소유자 리뷰를 대신하지 않습니다.


### W5 C 독립 구현·중단 후 재개

분석 접수/작업/소유자 이력·보고서·원본 다운로드/삭제, 계정별 실행·시간·멱등 제한, 네 보관 조합, grounding 검사, C 검증 사본 집계와 기동/만료 정리를 구현했습니다. 입력은 Q01 선정 전 비활성 opt-in TEXT만 준비했고 실제 D 분석기는 주입 전입니다. 실제 성공 mock을 기본값으로 넣지 않았습니다. 현재 worker는 단일 프로세스 내부 task이며 분산 실행 전 기존 queue로 이전해야 합니다.

재개 후 검토에서 REACTIVATE의 zero proof/빈 bytes를 ABI와 맞췄고, 철회는 실제 REVOKED 상태에 한해 확정하도록 보완했습니다. 만료된 미제출 작업은 체인/nonce부터 확인한 뒤 RESIGN을 안내합니다. 원본이 없어도 확인 가능한 정지/사고 경고를 유지하며 잘못된 기관/키 객체를 반환하는 Adapter는 거부합니다. 보관 기한 후 제거된 Operation의 서명 재접수도 500 대신 410입니다. 이 보완은 W5 누적 커밋에 포함되며 선행 범위의 Draft PR 리뷰에서도 함께 확인해야 합니다.

- 분석기 REFUSAL/TIMEOUT/RATE_LIMIT/INCOMPLETE_OUTPUT는 제한된 code로 구분하고 원시 예외 내용은 노출하지 않습니다. 해당 네 회귀는 후속 650e85c에 포함됩니다.
- 검증 코드 SHA: `650e85cd939ac4be493e14b4004daf081f92afa9`.
- 환경: macOS arm64, Python 3.13.0, FastAPI 0.142.2, Starlette 1.7.0, pytest 9.1.1, PostgreSQL 16.4; 합성 기관/키/분석기·Registry 증거.
- 전체 Python: API/core/analyzer/indexer/scripts 명시 경로 494 PASS / 외부·live opt-in 9 SKIP, 기존 TestClient deprecation warning 1. 신규 wallet HTTP/분석 검사는 45개입니다.
- 별도 실제 PostgreSQL 검사 1 PASS: 동시 발행 202/409·Operation 1개, 동시 분석 202/429·processor 실행 1회, 신규 지갑 모드 readiness. 체인 증거는 합성이며 실제 Registry 동시성 검사는 아닙니다.
- Migration 0001→0009 및 0009→0008→0009·schema check 통과. 앞선 0007 왕복·0008 적용 결과도 위 기록에 보존합니다. 사용자 DB/기존 Docker 서비스는 변경하지 않았습니다.
- Foundry offline: 기존 Contract + 지갑 Golden 26 PASS. 실제 새 Registry 구현의 테스트가 아닙니다.
- 두 템플릿 Node Web Crypto·생성 TypeScript 단독 컴파일·Makefile 범위 Ruff/compileall·구조·diff 검사 통과. 5개 생성기 재실행 결과 일치, 기존 v1/v2 Golden byte 동일, 새 Golden은 revision 표기만 변경됐고 digest/서명은 동일합니다.
- 실제 PostgreSQL 첫 재개 검사는 동시성 검사를 통과했으나 readiness에서 개인 `.env`의 구 기관 ID/projection 설정 때문에 실패했습니다. 합성 fixture 설정을 환경과 분리한 뒤 빈 임시 DB에서 재실행해 통과했습니다. 기능의 readiness 조건을 완화하지 않았습니다.
- 최초 광역 Ruff 명령은 설치된 외부 forge-std Python 도구까지 검사해 외부 코드 26건이 나왔습니다. 외부 코드를 수정하지 않고 기존 Makefile의 `apps packages/python services scripts` 범위에서 통과했습니다.

실제 실행 경로·환경·B/A/D 연결 요구·retention·rollback·오류 예시는 [C API 인계](../api/v5_c_runtime.md)를 사용합니다. 공유 계약 0.2는 additive 참조/오류 필드와 근거 제한을 반영하고 EIP-712/domain/schema/ABI를 유지합니다. 실제 Registry·A 지갑/브라우저·D 모델·유료 평가·공개 배포·G07 혼합 환경·처리 성능·작성자 외 리뷰는 미실행입니다. W1~W7 전체 완료로 판정하지 않습니다.

## 작업 브랜치·검증 기준

보존된 과거 phase/W1~W4는 그대로 보존합니다. 아래는 새 5.1 준비 stack으로, 각 후속 PR은 바로 앞 자기 브랜치를 기준으로 차이를 검토하고 새 단계 통합 시 retarget/선행 반영을 조율합니다. integration/main에는 자동 병합하지 않습니다. 첫 baseline에는 C6의 기존 누적 소스(당시 A/B/D 자산 포함)가 재사용되므로 새로 작성한 코드와 구분합니다.

| 범위 | 자기 브랜치 | 구현 SHA | 원본/책임 |
| --- | --- | --- | --- |
| 재사용 기준 | feat/v5-w1-c-reuse-baseline | 7056a57 | C6+integration 누적 기준 ba8946c 유지 |
| nonce 수정 | fix/v5-w2-c-nonce-cleanup | 4a0e6fb | B #50의 저장 실패/취소 수정만 C6 흐름에 반영 |
| 기관 확인·제안 | feat/v5-w2-c-governance | a303ec6 | C DB/API, 실제 B Adapter는 후속 |
| 발행·검증 | feat/v5-w3-c-publication | 7913435 | C 저장/검증/직접 거래 대조 |
| 버전·철회 | feat/v5-w4-c-document-lifecycle | 12ddb35 | C lifecycle, 실제 체인 전이는 후속 |
| 분석·보관·집계 | feat/v5-w5-c-analysis-retention | 30002bc + 650e85c | C 독립 구현+위 경계 보완, 실제 D 모델은 후속 |

clean 사본은 git archive로 커밋 파일만 푼 뒤 개인 .env 없이 frozen 의존성을 새 환경에 설치해 재현합니다. 최종 커밋 650e85c의 clean 사본에서 uv sync --all-packages --all-groups --frozen --offline 후 전체 494 PASS/9 SKIP·Ruff·구조 검사를 재현했습니다. 신규 의존성은 추가하지 않았습니다. 30002bc 사본에서 최초 frozen 설치 시 캐시에 없는 고정 패키지만 원래 배포처에서 받았고 최종 사본은 offline 설치했습니다. 사용자님의 명시적 승인 후 여섯 작업 브랜치를 원격에 push하고 Draft PR #57~#62를 생성·대화에 첨부했습니다. [여섯 PR의 URL·head/base·본문](v5_c_pull_requests.md)을 확인합니다. 원격 CI·소유자 리뷰 완료는 별도입니다. 작성자 외 리뷰는 미확인입니다.

검증 전용 PostgreSQL 컨테이너는 검사 후 정리했습니다. 기존 사용자 서비스와 DB는 유지했습니다.

## 원격 공유 결과

- [#57](https://github.com/OriginProof-3web/OriginProof/pull/57): `feat/v5-w1-c-reuse-baseline` → `integration`, Draft.
- [#58](https://github.com/OriginProof-3web/OriginProof/pull/58): `fix/v5-w2-c-nonce-cleanup` → `feat/v5-w1-c-reuse-baseline`, Draft.
- [#59](https://github.com/OriginProof-3web/OriginProof/pull/59): `feat/v5-w2-c-governance` → `fix/v5-w2-c-nonce-cleanup`, Draft.
- [#60](https://github.com/OriginProof-3web/OriginProof/pull/60): `feat/v5-w3-c-publication` → `feat/v5-w2-c-governance`, Draft.
- [#61](https://github.com/OriginProof-3web/OriginProof/pull/61): `feat/v5-w4-c-document-lifecycle` → `feat/v5-w3-c-publication`, Draft.
- [#62](https://github.com/OriginProof-3web/OriginProof/pull/62): `feat/v5-w5-c-analysis-retention` → `feat/v5-w4-c-document-lifecycle`, Draft.

선행 순서대로 검토하며 코드 검증 SHA 650e85c 이후에는 문서·공유 기록만 추가했습니다. integration/main·과거 phase는 변경하지 않았습니다. 원격 CI·작성자 외 리뷰는 후속이며 단계 전체 완료로 판정하지 않습니다.


### 원격 CI의 선행 생성물 보완

최초 #57/#58 python-quality는 `make generate` 뒤 api.ts의 IssueInput.content가 unknown에서 PaymentIssue | DocumentIssue로 바뀌어 실패했습니다. 근거: [#57 초기 CI](https://github.com/OriginProof-3web/OriginProof/actions/runs/38847390740), [#58 초기 CI](https://github.com/OriginProof-3web/OriginProof/actions/runs/38847390636). 생성기로 한 줄을 갱신한 `b82a2d1`을 #57에 추가하고 뒤의 자기 브랜치에 순서대로 병합했습니다. 후속 최종 코드에는 이미 같은 생성 타입이 있어 Python/생성물/Golden은 검증 코드 650e85c와 동일합니다. 과거 단계·다른 담당 브랜치를 변경하거나 force push하지 않았습니다.

선행 기준에서 다섯 생성기 재실행 일치·생성 API TypeScript 컴파일·diff 검사를 통과했습니다. 새 원격 CI 결과는 재실행 중이며 초기 실패를 전체 통과로 덮어쓰지 않습니다. 작성자 외 리뷰와 실제 B/A/D 연결은 계속 후속입니다.

## V5-W6-C 신규 지갑 복구·독립 검증 (2026-10-16)

사용자 요청으로 잔여 C 작업을 진행했습니다. 사용자 확인과 원격 branch/PR 점검에서 새 B Registry/Adapter와 D 분석기는 아직 없으므로 실제 연결은 대기합니다. 기존 W1~W5 PR을 보존하고 `feat/v5-w6-c-recovery-integration`을 #62 head `eaa0d166269833cf7ee49675cfa777b0208c3725`에서 시작했습니다.

- 검증 코드 SHA: `c17a8f573bc8f64b522637cd3178f893baec8316`. 이후 기록 커밋은 문서만 변경합니다.
- 새 migration·서비스 API/기본 mock·의존성 변경은 없습니다. 기존 `test_w6_c_recovery`의 프로세스/HTTP 도구, C 앱 factory·검증 코어·공유 ABI·Golden·고정 lockfile을 재사용했습니다. B/D 소유 생산 코드는 수정하지 않았습니다.
- `make test-v5-c-live`: 실제 PostgreSQL 16.4/uvicorn HTTP 프로세스 **5 PASS**. 0006 구자료를 유지한 head 적용·새 DB pg_restore·버전별 원본/서명·분석 동의/보관·SIGKILL·UNKNOWN 단일 제출·확정 저장 실패/재조회·worker 재시작/늦은 결과·동시 버전/권한·RPC 장애/만료를 확인했습니다. Registry/분석기 증거만 합성이며 전용 자원을 정리했습니다.
- 독립 CLI `scripts/verify_wallet_document.py`: 로컬 자료와 별도로 지정한 신뢰 chain/address·직접 RPC만 사용합니다. 두 템플릿, 변경/누락 증거, 고정 block/reorg, 과거 키/사고, ABI 일치, 잘못된 로컬 입력을 포함해 **33 PASS**입니다. 실제 새 배포에서 V5-F20을 완료한 근거는 아닙니다.
- 전체 Python 명시 경로 **527 PASS / 14 SKIP / 기존 warning 1**. 14개에는 opt-in 신규 live 5개와 기존 9개가 포함됩니다. 별도 기존 `W6_C_LIVE_TEST=1` 복구는 **2 PASS**이며 실제 Anvil을 포함합니다. 기존/신규 Registry 근거를 혼합하지 않습니다.
- `c17a8f5` git archive 사본에 개인 `.env` 없이 `uv sync --all-packages --all-groups --frozen --offline` 후 전체 **527 PASS / 14 SKIP**를 재현했습니다. Makefile 범위 Ruff·신규 Python format·compileall·diff 검사도 통과했습니다.
- 성능 기준: 실제 HTTP/PostgreSQL에서 서로 다른 request ID의 보호 필드 검증 100회 모두 VERIFIED. p50 **13.15ms**, p95 **14.22ms**. `build/v5-c-performance.json`/CI 로그에 범위를 남깁니다. 합성 Registry·단일 순차 실행 기준이며 실제 RPC/모델/부하 성능·개선율을 뜻하지 않습니다.
- 환경: macOS arm64, Python 3.13.0, uv 0.8.17, PostgreSQL 16.4, FastAPI 0.142.2/Starlette 1.7.0/pytest 9.1.1. `uv.lock` SHA-256: `e5122f523c7bc1e1bedf6795244cbdd2baaaeec9dc9c7f3fb088e2f064806dd6`. 기존 `scripts/ci/environment_fingerprint.py`로 SHA·도구·잠금 파일도 기록했습니다.

[복구·독립 검증 runbook](../api/v5_c_recovery_runbook.md)에 백업 자료/권한·빈 DB 복원·UNKNOWN 정책과 B/A/D의 실제 연결 지점을 정리했습니다. [W6 C 기여 기록](../portfolio/W6-C.md)의 5.1 절에 재사용·실패 분석·AI 활용·미완료를 연결합니다.

다음 담당/조건: B의 실제 Registry·canonical Adapter/manifest·G07, D의 선정 입력/모델·독립 재현, A의 실제 지갑/화면 소비·소유자 리뷰가 준비되면 같은 후보로 연결합니다. C는 해당 연결의 API/DB 결함과 후보/lockfile/migration/manifest를 정리합니다. 실제 모델 평가·다른 PC·서비스 API 밖 실제 배포 검증·전체 리허설 3회가 없어 통합 RC 또는 W6/W7 전체 완료로 판정하지 않습니다.
