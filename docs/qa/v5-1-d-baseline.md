# 계획서 5.1 · D 개발 기준 반영 기록

- 확인일: 2026-10-15, 한국시간. 범위는 기준 반영·재사용 인계 확인이며 새 기능 구현은 없습니다.
- 개발 작업 폴더: `/Users/home/Workspace/OriginProof-worktrees/w1-d`.
- 개발 브랜치: `codex/v5-1-d-baseline`. 기존 `codex/w1-d-qa`의 `54f09e4e8db162db078c9347015c47cae881301d`에서 분기했습니다.
- 반영 기준: [PR #56](https://github.com/OriginProof-3web/OriginProof/pull/56), `origin/integration`의 `33bc4f4e7456c5ef7c2df8c8bf09f8014e0169f8`. GitHub의 MERGED·base integration·2026-10-15 01:48 한국시간과 fetch 결과를 확인했습니다.
- 계획서 **5.1**은 5.0 기능 범위를 유지합니다. 공통 계약은 **v5-shared-0.1**이며 실제 API·Registry·DB·브라우저 지갑 연결 완료와 구분합니다.

## 보존과 병합

최초 폴더 `/Users/home/Workspace/OriginProof`는 `mvp/ai`가 가리키는 유효한 HEAD 커밋과 index가 없고 모든 소스가 미추적 상태였습니다. 기존 착수 기록에서 실제 D 개발 작업 폴더를 확인했고, 최초 폴더의 파일은 수정하지 않았습니다. `.git`을 제외한 전체 백업의 4,548개 파일 hash를 검증했습니다.

- 최초 폴더 백업: `/private/tmp/originproof-pre-v5-1-4s6vb2zv/workspace.tar.gz`, 파일별 hash는 같은 폴더의 `sha256.json`.
- D 개발 폴더의 병합 전 tracked 188개 경로: 같은 백업 폴더의 `w1-d-tracked.tar.gz`, `w1-d-sha256.json`.
- 기존 D 폴더는 미커밋 변경이 없었습니다. 원래 로컬 작업 브랜치와 phase/integration 브랜치를 직접 수정하지 않았습니다.
- 최신 integration을 병합한 커밋: `8c716a482dbe08db3a8932b050b5845829102aa2`. 충돌 없이 병합됐습니다.
- 같은 D 원격 브랜치에만 있던 기존 검증 기록 `5a55949ff146a7dedfd89a531a494b03df151333`도 병합했습니다. 변경은 `docs/qa/w1-results.md`의 과거 E2E 기록 25줄이며 재실행 결과로 합산하지 않습니다.
- 인계 기록까지 포함한 검사 기준 HEAD: `1117af25ace462c7ca36c06a107bc58be28667be`. `8c716a4`와 실행 코드·검사·fixture·생성물·lockfile이 같습니다. 이후 변경은 이 기록과 현재 PR 상태 문서뿐입니다.
- #56 변경 52개 경로가 병합본과 동일함을 확인했습니다. 이후 계획서 3.1·15장과 인계 문서의 현재 Draft 표기만 실제 병합 사실로 갱신하고 17.4절의 병합 전 기록은 당시 이력으로 명시했습니다.
- 기존 W1-D fixture·회귀 검사·개인 기여 기록을 보존했습니다. 과거 PR 전체를 순서대로 재병합하거나 생성물을 손으로 수정하지 않았습니다.

## D 영역의 재사용 인계 확인

[재사용 인계 원본](../handoffs/v5_reuse_handoff.md)의 고정 SHA와 [계획서](../development_plan.md) 4·12·14장을 비교했습니다. 아래 항목을 새 기능 완료나 D의 전체 소비 리뷰 승인으로 처리하지 않습니다.

| 항목 | 현재 포함·보존된 내용 | 남은 작업 |
| --- | --- | --- |
| R39 · `ab86892f1aedc14664e3129231225e79220b7394` | 기존 D W1 QA·합성 사례·v1 회귀·기여 기록 유지. 고정 원본의 v1 QA 회귀 파일은 동일하지만 fixture 생성기·사례·검사·기여 문서는 차이가 있습니다. | 고정 원본 전체 채택은 하지 않았습니다. C 조율 후 v2 기반과 새 계약에 적용할 차이를 선정하고 실제 연결을 재검증합니다. |
| R51 · `17f78e300b04aa9395fb20f6f76f5313d705db3d` | 인계 내용과 과거 브라우저 6 PASS/6 FAIL의 구분을 확인했습니다. 해당 helper·브라우저 spec·보고서는 현재 브랜치에 없습니다. | A의 R54/R55 수정과 비교해 신규 기관·공동승인·지갑 흐름으로 D 독립 재검사합니다. 과거 FAIL을 PASS로 바꾸지 않습니다. |
| R43 · `c16de660914389ba8821612aa3d6c64708085185` | 기존 provider·오류·후보 추출 기반은 있습니다. 현재 service는 고정 원본과 다르고 v4 prompt·안전성 검사·확인 인계는 포함되지 않았습니다. | 입력 결정 뒤 기존 안전성 자산과 새 결과/확인/grounding 계약을 연결합니다. 헤더만으로 확인·근거 대조가 강제되지 않는 한계를 유지합니다. |
| R55 / R37 / R38 관련 D 검증 | #52의 W5 QA·실패 문서는 integration에서 이미 반영됐으므로 중복 적용하지 않았습니다. | G07은 원인·해결 미확정입니다. B/C 원인 확인 후 D가 같은 후속 제품 SHA에서 재검사하며 보안·복구 원본은 새 계약에 맞춰 별도 채택합니다. |

G07의 과거 fresh 18 PASS와 mixed 17 PASS/1 FAIL은 그대로 보존합니다. 이번 기준 반영으로 해결 처리하지 않습니다. V5-W1-D의 fixture/평가 인계와 V5-W2~W7-D의 새 수용 검사는 후속 개발입니다. 공통 결과·오류·합성 텍스트 검사는 입력 회의 전에도 가능하지만, 입력 종류·우선순위(V5-Q01), 실제 모델·유료 평가 범위(V5-Q05)는 확정하지 않았습니다. Decisions API는 현재 범위 밖입니다.

## 실행 검사

Python 실행 코드의 검증 SHA는 `8c716a482dbe08db3a8932b050b5845829102aa2`입니다. 이후 HEAD `1117af2`는 위에서 설명한 과거 문서 기록만 추가했으며 코드 차이가 없습니다. PostgreSQL·실제 RPC·지갑 연결의 성공으로 아래 결과를 해석하지 않습니다.

| 검사 | 결과·검사 경계 |
| --- | --- |
| `UV_PROJECT_ENVIRONMENT=.uv-venv uv run --locked --offline --all-packages --all-groups pytest -q` (workspace PYTHONPATH) | **171 PASS**, skip 0, Starlette/anyio deprecation warning 1. API 단위/ASGI·in-memory/mock·코어/서명·Analyzer·fixture 검사이며 실제 서비스 연결 검사가 아닙니다. |
| `make generate` (기존 uv 환경, offline/locked) | v1 Schema/타입/Golden과 신규 Schema/TS/예정 OpenAPI/Golden/예시/Solidity Golden 재생성 후 **diff 없음**. |
| `node scripts/ci/check_wallet_browser_hashes.mjs` | 두 템플릿의 원본·보호 hash·필드 대조 **PASS**. 호스트 Node 24.8.0 Web Crypto이며 실제 브라우저 지갑 검사가 아닙니다. |
| 현재 Contract 소스의 `forge test --root /tmp/contracts --offline` | 읽기 전용 소스를 복사한 격리 컨테이너에서 **14 PASS / 0 FAIL / 0 skip**, 신규 Golden 4개 포함. 기존 fuzz 1개의 512회 실행을 512개 검사로 합산하지 않습니다. Foundry 1.4.4 / solc 0.8.26, 고정 OpenZeppelin 5.7.0·forge-std 1.16.2. |
| 컴파일 ABI 대조 | 같은 소스의 `out/IOriginProofWalletRegistry.sol/IOriginProofWalletRegistry.json`의 ABI와 커밋된 ABI가 **동일**합니다. 신규 Registry 구현·배포 검사는 아닙니다. |
| 생성 TS 컴파일 | 기존 웹 이미지 TypeScript 5.8.3으로 `tsc --noEmit --strict --skipLibCheck --target ES2020` 실행, `wallet-contract.ts`·`originproof.ts` **PASS**. 전체 웹 연결 검사는 아닙니다. |
| `.uv-venv/bin/ruff check --no-cache apps packages/python services scripts` | **PASS**. 기본 cache 위치의 sandbox 쓰기 제한은 no-cache로 우회했습니다. |
| `python -m compileall -q apps packages services scripts` | 임시 pycache 경로에서 **PASS**. Python 정적 타입 검사와 구분합니다. |
| `make bootstrap-check env-fingerprint` | 구조·환경 점검 **PASS**. Python 3.13.7 / uv 0.8.17 / pnpm 11.19.0 / Docker 29.7.2, 실제 fingerprint는 로컬 `build/environment_fingerprint.json`. 호스트 forge는 없고 위 Contract 검사는 기존 Docker 이미지에서 실행했습니다. |
| 문서·보존·생성물 확인 | 필수 문서의 로컬 링크 89개 중 저장소 내 대상 85개 존재. 계획 버전·D 작업 ID 7개·V5-F01~21·PR 병합 상태·생성물 일치와 `git diff --check` 확인. SG01~16의 `NOT_EXECUTED` 상태를 유지합니다. |

Contract·TypeScript 컨테이너는 `--network none`과 현재 소스의 읽기 전용 mount를 사용하고 종료했습니다. 기존 서비스·DB·배포·사용자 환경을 초기화하지 않았습니다.

## 미해결·미실행

- 기능 동작·계약 판단을 요구하는 병합 충돌은 없습니다. 신규 서비스 기능 구현과 원격 push·PR 생성·원격 병합은 하지 않았습니다.
- 신규 API/Registry/DB migration/실제 PostgreSQL·RPC·브라우저 지갑·공개 네트워크, 전체 웹/실제 E2E, v2 권한·consume의 실제 연결, G07 재현/수정, 실제 유료 모델 평가는 **미실행**입니다. 기존 v1/v2 자료·서명·권한·consume 원본/회귀는 삭제하거나 신규 계약으로 바꾸지 않았습니다.
- 계획서의 저장소 밖 과거 참고자료 링크 4개는 이 작업 폴더에 없습니다: 기획서 PDF, `originproof_integrated_development_plan.md`, `Init_files/originproof_human_start_guide.md`, `M1_BACKEND_START_CHECKLIST.md`. 기존 기준본에도 있던 링크이며 파일을 만들어 대체하지 않았습니다.
- B/A/D 소유자·소비 리뷰와 사람의 기여 확인을 받았다고 기록하지 않습니다. 이번 작업은 기존 구현·문서를 보존한 기준 반영과 독립 검사·인계 확인입니다.
