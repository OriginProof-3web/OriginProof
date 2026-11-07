# B 영역 v5 기준 반영 · 인계 확인

- 확인일: 2026-10-16, 한국시간. 기능 구현 착수나 단계 완료 기록이 아닙니다.
- 개발 브랜치: `codex/v5-b-baseline`. 시작 HEAD: `987dc2522048cb7df0fb42f5df650501fe5f2fd7`.
- `git fetch origin` 후 #56 MERGED 확인. 병합 시각: 2026-10-15 01:48:06 KST.
- 반영한 integration/#56 병합 SHA: `33bc4f4e7456c5ef7c2df8c8bf09f8014e0169f8`.
- 계획서 **5.1**은 5.0 기능 범위를 유지합니다. 공유 계약 준비 버전은 **v5-shared-0.1**입니다.
- 검증 대상은 위 integration과 시작 HEAD의 병합 결과 및 아래 충돌 해결입니다. 최종 로컬 병합 SHA는 `git log -1 --format=%H`로 확인합니다.

## 보존과 충돌 해결

원본 브랜치 `mvp/chain-integration` 및 과거 phase/다른 worktree는 이동하지 않았습니다. 시작 HEAD는 병합의 첫 부모로 남습니다. 미커밋/미추적 원본은 저장소 밖 `/Users/hamin/Desktop/blockchain-baseline-backup-20261016-152053`의 binary patch·파일 archive·SHA-256 목록과 `v5-baseline preserve local work 987dc25` stash에 이중 보존합니다. 원본 사용자 변경은 병합 커밋과 분리하여 작업 폴더에 복원합니다. stash는 삭제하지 않습니다. 기존 ignored 환경·Foundry 의존성도 제거하지 않습니다.

9개 충돌 파일은 최신 환경/Makefile/지침을 기본으로 개별 조정했습니다. `.gitignore`는 최신 규칙을 사용합니다. API의 기본 `JsonRpcBlockchainReader`는 최신 manifest/string ID 경로이며 기존 bytes Reader는 `rpc_reader.py`와 `LegacyJsonRpcBlockchainReader` export로 보존합니다. 기존 모델/port/검사는 유지합니다.

SQLAlchemy projection과 최신 검사는 기본 경로입니다. 기존 SQLite 구현은 `legacy_projection.py`, 기존 네 검사는 `test_legacy_projection.py`에 보존합니다. 두 DB 표현을 자동 변환하거나 혼합하지 않습니다. 최신 `DeployLocal.s.sol`과 Python 배포 경로를 유지하고 기존 private-key 기반 로컬 스크립트는 `LegacyDeployLocal.s.sol`/`deploy-local-legacy`로 구분합니다. 기존 chain/bootstrap/export 명령도 유지합니다. 새 Registry 배포나 기존 배포 주소 변경은 수행하지 않습니다.

Python은 최신 3.13 workspace를 사용합니다. 기존 Reader 검사에 필요한 eth-abi/respx와 전이 의존성만 lock에 추가하고 integration의 모든 기존 패키지 버전을 유지했습니다. 동명 테스트 수집 충돌은 기존 모델 테스트 파일을 `test_legacy_models.py`로 구분해 해결했습니다. 테스트 본문은 유지합니다.

## B 담당 재사용 인계

[원본 인계](../handoffs/v5_reuse_handoff.md)와 [계획서](../development_plan.md)의 4·12·14장을 확인했습니다. 종료된 PR은 고정 SHA 비교 원본이며 전체 재병합하지 않았습니다.

| 항목 | 이미 포함·확인한 내용 | 남은 범위 |
| --- | --- | --- |
| R39 / `ab86892f1aedc14664e3129231225e79220b7394` | 기존 Issuer/Key Registry·ABI·Reader/projection 기반과 공유 준비 모델을 구분 | Writer/manifest 및 신규 권한·서명 경계의 적용 선정·검토 |
| R55 / `56dbd82407e7d04cca97162aebbf276ec6a9f607` | 누적 UI/API/체인 원본이며 R54/R53/R48 중복 관계 확인 | 신규 지갑/문서·버전 연결, G07 원인 확인·독립 재검사 |
| R37 / `9651062c9f36e124b76796278c996764678e1c77` | Reader/SQLAlchemy projection의 중복·checkpoint·명시적 reorg 검사 기반 | Writer/Operation·scanner/신규 이벤트·실제 DB 연결 재사용 선정 |
| R38 / `3ef1fd40943914c1450e8bc05047119ab7eabbc0` | R37을 포함하는 후속 원본으로 비교, 이중 적용 없음 | 제출 참조 검증·UNKNOWN·재시작·복원 검사의 신규 계약 적용 |

위 원본에 있는 `writer.py`, `manifest.py`, `ProofStatusRegistry` 및 관련 lifecycle/consume·복구 검사 일부는 현재 integration/시작 브랜치에 없습니다. 이를 이번 기준 반영에서 새로 병합하거나 구현하지 않았습니다. 과거 브랜치/고정 SHA를 보존하며 신규 공개 안내에 레거시 gateway·consume을 자동 적용하지 않습니다. 이번 통과는 v2/consume 회귀 전체 실행을 뜻하지 않습니다.

다음 B 작업은 V5-W1-B의 계약 차이/Golden 소유자 검토, W2-B 공동승인/정지, W3-B 기관 서명/소유권/nonce, W4-B 원자적 다음 버전/철회/키 이력, W5-B 이벤트/현재 상태 연결, W6-B 복구/G07, W7-B 최종 배포 동결입니다. 이번에는 착수하지 않았습니다. 소유자·소비자 리뷰나 인계 항목 완료를 대신 기록하지 않습니다.

## 검증 결과

- `uv sync --all-packages --all-groups`: Python 3.13 별도 `.uv-venv`; 기존 `.venv` 보존. 기존 integration lock 패키지 버전 변경 없음.
- `UV_PROJECT_ENVIRONMENT=.uv-venv uv run --locked --all-packages --all-groups pytest -q`: **179 PASS / 1 SKIP**. 합성/mock·SQLite/ASGI 검사 포함; SKIP은 실제 EVM opt-in입니다. anyio alias deprecation 경고 1개.
- `PATH=$HOME/.foundry/bin:$PATH M4_LIVE_TEST=1 UV_PROJECT_ENVIRONMENT=.uv-venv uv run --locked --all-packages --all-groups pytest -q services/indexer/tests/test_live_chain.py`: **1 PASS**. 별도 임시 Anvil의 실제 배포/Reader/API 정상·금액 변조·정지·키 철회·RPC 중단 검사입니다. 실제 PostgreSQL·브라우저 지갑 검사가 아닙니다.
- `forge test --root packages/contracts --offline`: **14 PASS**. 기존 Registry 10개와 준비 서명 Golden 4개; fuzz 512회. 신규 Registry 런타임 검사가 아닙니다.
- `make generate`: Schema·TypeScript·OpenAPI·기존/신규 Golden·합성 예시·컴파일 ABI 재생성 후 integration 대비 차이 없음. 생성 파일 수동 수정 없음.
- `node scripts/ci/check_wallet_browser_hashes.mjs`: 두 템플릿 원본/보호 hash·필드 교차 검사 PASS.
- `uv run --locked ruff check apps packages/python services scripts`, repository structure, diff whitespace: PASS.
- 필수 9개 문서의 로컬 링크 89개 검사: 저장소 내부 경로 정상. 계획서의 저장소 밖 기획 자료 4개가 현재 환경에 없음: `찐품명품_기획서.pdf`, `originproof_integrated_development_plan.md`, `Init_files/originproof_human_start_guide.md`, `M1_BACKEND_START_CHECKLIST.md`.
- `scripts/ci/env_check.py`: **FAIL**, `.env` 없음. 설정/운영 값을 임의 생성하지 않았습니다.
- 미실행: 실제 PostgreSQL/migration/DB 복원·브라우저/지갑·공개 체인·유료 AI·웹 lint/typecheck/build/E2E·신규 Registry SG01~16·G07 재현/수정·v2/consume 전체 회귀.

## 남은 문제와 범위

G07은 미해결입니다. fresh 성공이나 이번 기준 반영으로 해결 처리하지 않습니다. 공유 모델/인터페이스/예정 OpenAPI는 Registry/API/DB/지갑 연결 완료가 아닙니다. 입력 종류·우선순위는 회의 후 확정하고 Decisions API는 현재 범위 밖입니다. 기존 v1/v2 자료·서명·권한·consume은 별도 호환 경로와 과거 원본으로 보존합니다.

계획서 3.1절과 원본 인계 2절의 “#56 Draft/미병합”은 작성 당시 snapshot이며 현재 GitHub MERGED 상태와 다릅니다. 원본 문구는 보존하고 이 기록에 현재 상태를 구분했습니다. 계약/기능 판단이 필요한 병합 충돌은 남아 있지 않습니다. 원격 push·PR 생성·원격 병합은 수행하지 않습니다.
