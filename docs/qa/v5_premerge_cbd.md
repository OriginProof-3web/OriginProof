# V5 C·B·D 머지 전 통합 검증 — 2026-10-17

이 문서는 사용자가 승인 추천 대상으로 지정한 12개 PR을 함께 적용할 때의 충돌 해결과 검증 근거입니다. 검증용 Draft 후보이며 단계 완료·실제 신규 지갑 연결·integration 병합을 뜻하지 않습니다.

## 기준과 포함 범위

- 담당: C `@Jordi2801K`의 통합 조율. 사용자가 승인한 범위에서 Codex가 충돌 해결·검사·기록을 수행했습니다. 다른 팀원의 구현·저자·사람 리뷰를 대신 주장하지 않습니다.
- 브랜치: `codex/v5-premerge-cbd`; 시작 `integration@33bc4f4e7456c5ef7c2df8c8bf09f8014e0169f8`.
- 기능 코드 검증 SHA: `f68799f88e75256ddaec4e19580e4430da4e27b2`. 이후 이 보고서·구조화 근거·C 기여 기록은 문서만 추가합니다.
- 기준 PR 3개 검증 SHA: `5bfb098220763a05d45516b096e637aea5a599a8`; 로컬 보존 브랜치 `codex/v5-premerge-baselines`.
- merge commit으로 원래 커밋과 작성자 이력을 보존했습니다. 기존 20개 PR의 head/base/Draft 상태와 원격 integration은 바꾸지 않았습니다.
- 제외: C #59–63, B #69, D #75–76. 이 8개 head가 후보의 조상이 아님을 검사했습니다. C #57에 이미 포함된 이전 계획의 누적 개발은 재사용 기준으로 포함됩니다.
- 현재 작업은 단계 밖의 통합 준비입니다. 기존 단계별 PR과 기록을 보존하며 phase 승격·완료로 사용하지 않습니다.

| 포함 PR | 고정 head | 원래 base |
| --- | --- | --- |
| [#57](https://github.com/OriginProof-3web/OriginProof/pull/57) | `b82a2d1842c1ba9d03e21deff50c840841ab680a` | `integration` |
| [#58](https://github.com/OriginProof-3web/OriginProof/pull/58) | `bfbf1fbf7d3fcacf4326e68c4a4878d3576b119d` | `feat/v5-w1-c-reuse-baseline` |
| [#64](https://github.com/OriginProof-3web/OriginProof/pull/64) | `9feec138bf3d6d8a379b211583f92db1716e54f2` | `integration` |
| [#65](https://github.com/OriginProof-3web/OriginProof/pull/65) | `c2111e379889d8550aa6ff893d44f576fb78189a` | `codex/v5-b-baseline` |
| [#66](https://github.com/OriginProof-3web/OriginProof/pull/66) | `5f91ac8e3405ac2f3bbe9ae19e15b81dd1f58c6e` | `codex/v5-w1-b-contract-review` |
| [#67](https://github.com/OriginProof-3web/OriginProof/pull/67) | `004f774e89a278ec8ab4c5dba233d0d7c3eb0a97` | `codex/v5-w2-b-governance` |
| [#68](https://github.com/OriginProof-3web/OriginProof/pull/68) | `a4bfa22bf870f3bd5ae02e439636fbf8204444a7` | `codex/v5-w3-b-publication` |
| [#70](https://github.com/OriginProof-3web/OriginProof/pull/70) | `854ee66274dea388b9c5608bd385d9e8a8d258f2` | `integration` |
| [#71](https://github.com/OriginProof-3web/OriginProof/pull/71) | `1ac2169acfe5a92a0185010e9a27720ab9651be5` | `codex/v5-1-d-baseline` |
| [#72](https://github.com/OriginProof-3web/OriginProof/pull/72) | `17774fb89d5c0efa70f548f697a320ad152ff632` | `codex/v5-w1-d-safety-qa` |
| [#73](https://github.com/OriginProof-3web/OriginProof/pull/73) | `4b6f73bec57aa10f28b29901f86e74852dfd2ff6` | `codex/v5-w2-d-governance-qa` |
| [#74](https://github.com/OriginProof-3web/OriginProof/pull/74) | `a6b8f04930e809cec8136e99a782c8fbdc8b1d7e` | `codex/v5-w3-d-content-qa` |

## 충돌 해결

B #64 → D #70 → C #57 순서로 별도 로컬 후보에 적용했습니다. 실제 Git ort 병합에서는 최초 공용 파일 4개를 직접 해결했고, fixtures README의 W1/W3 내용은 자동 병합됐습니다. 이후 C #58, B #65–68, D #71–74를 추가할 때 문서 7개에서 충돌을 해결했습니다.

| 파일 | 처리 |
| --- | --- |
| `.env.example` | C의 보안·합성 발행 설정과 B의 legacy 체인 설정을 용도 구분해 모두 보존. |
| `Makefile` | 실제 pip-audit·복구·Finals 명령을 유지하고 legacy 배포/체인 명령 추가. 기존 보안 안내문으로 되돌리지 않음. |
| `apps/api/src/infrastructure/blockchain/__init__.py` | C/B의 14개 export 합집합 유지. 기본 Reader/Writer와 명시적 Legacy Reader의 실제 클래스 identity 확인. |
| `pyproject.toml`, `uv.lock` | C 기존 잠금 버전 전부 보존, B의 eth-abi/respx와 전이 의존성 parsimonious/regex 추가. 병합 선언으로 uv lock 재생성. B의 pytest pythonpath/indexer 테스트 경로 유지. |
| `fixtures/finals/README.md` | 기존 W1·W3 설명과 신규 V5 소비 QA 설명을 모두 보존. NOT_RUN 의미 유지. |
| `docs/handoffs/v5_reuse_handoff.md` | #56 실제 병합 시각·확인 시점과 B/D 후속 인계 내용을 보존. |
| `docs/portfolio/W1-B.md` ~ `W4-B.md`, `W3-D.md` | V5 기록과 이전 계획의 기여 기록을 함께 보존. 과거 검사/미확인을 현재 완료·승인으로 바꾸지 않음. |

수동 생성물 수정·새 인터페이스·의존성 버전 일괄 상승은 하지 않았습니다. README·기여 기록 원문과 export 보존, 충돌 마커·미해결 index 부재를 별도 assert로 확인했습니다.

## 실제 로컬 검증

| 검사 | 실제 결과 | 의미 |
| --- | --- | --- |
| 기준 3개 Python | 457 PASS / 8 SKIP | 기준 조합 회귀. |
| 승인 대상 12개 Python | 500 PASS / 8 SKIP | 기본 전체 pytest; opt-in 8개는 기본 실행에서 제외. |
| Foundry | 100 PASS / 0 FAIL / 0 SKIP | 기존 Registry/Proof 회귀와 B 신규 wallet Contract; fuzz 각 512회. |
| 기존 C 실제 복구 | 2 PASS | 매 검사 임시 PostgreSQL·Anvil·별도 API 프로세스. 강제 재시작/UNKNOWN 복구와 pg_dump/restore·signer 보존·migration·배포 식별. |
| Ruff·compileall·구조 | PASS | Python 정적/문법 및 저장소 구조. |
| make generate + 생성물 diff | PASS / 변경 없음 | Schema·Golden·타입·OpenAPI가 원본과 일치. |
| make security | 알려진 취약점 없음 | 통합 Python 잠금 파일의 pip-audit 결과. |
| 웹 lint·typecheck·build | PASS | 생성 타입을 소비하는 기존 웹의 정적 검사·빌드. |
| 웹 단위 | 8 PASS | 기존 화면 회귀. |
| Playwright Chromium | 5 PASS | 자체 Next dev 서버·mock HTTP E2E. 실제 신규 지갑/API 연결 증거 아님. |

핵심 실행 명령:

```sh
uv sync --python 3.13.0 --all-packages --all-groups --locked
.venv/bin/python -m pytest -q
UV_FROZEN=1 UV_OFFLINE=1 make generate UV_ENV=.venv
git diff --exit-code -- packages/schemas/generated fixtures/golden
.venv/bin/ruff check apps packages services scripts
.venv/bin/python -m compileall -q apps packages services scripts
.venv/bin/python scripts/ci/validate_structure.py
(cd packages/contracts && forge test --offline)
W6_C_LIVE_TEST=1 .venv/bin/python -m pytest -q scripts/ci/test_w6_c_recovery.py
UV_FROZEN=1 make security UV_ENV=.venv
corepack pnpm --filter originproof-demo-web lint
corepack pnpm --filter originproof-demo-web typecheck
corepack pnpm --filter originproof-demo-web test
corepack pnpm --filter originproof-demo-web build
CI=1 corepack pnpm --filter originproof-demo-web test:e2e
```

실제 복구 명령은 Docker와 고정 Foundry·Contract 라이브러리가 있는 폐기 가능한 합성 환경에서만 실행합니다. 기존 Compose/DB 볼륨은 사용하지 않았고, 검사에서 만든 컨테이너와 웹 서버가 종료됐음을 확인했습니다. 로컬 원시 로그/JUnit은 ignored `build/premerge/`, 지속되는 요약은 [구조화 근거](v5_premerge_cbd.json)입니다.

환경: macOS arm64, Python 3.13.0, uv 0.12.1, Node 22.14.0, corepack pnpm version 조회 11.19.0 / 의존성 설치 출력 11.25.0, Foundry 1.4.4, solc 0.8.26. Contract 라이브러리는 OpenZeppelin v5.7.0 / forge-std v1.16.2 고정 SHA를 사용했습니다. 원격 CI의 Linux/Node 22.18.0/uv 0.8.17 환경 재현은 PR의 새 검사 결과로 따로 확인합니다.

오프라인 uv/pnpm 설치는 패키지·레지스트리 메타데이터 캐시 부족으로 처음 실패했고, 고정 버전 그대로 온라인 재시도해 설치·정책 검사를 완료했습니다. Python 테스트의 기존 Starlette httpx deprecation 경고와 웹의 기존 CSS autoprefixer 경고가 있었으며 기능 검사는 통과했습니다.

## 남은 검토와 범위

- 이 통합 후보 자체의 작성자 외 리뷰는 아직 없습니다. 원 PR의 승인 결과가 새 통합 후보의 승인으로 이전된 것으로 기록하지 않습니다.
- 원래 C #57/#58은 작성자 본인 승인 불가로 다른 팀원의 확인이 남아 있습니다.
- 실제 신규 WalletRegistry Adapter ↔ 신규 C API/DB ↔ A 지갑 화면 ↔ D 분석기의 연결 검증은 이번 범위 밖입니다. 현재 후보의 실제 2개 복구 검사는 이전 호환 경로입니다.
- D의 `fixtures/finals/v5_d_w2_governance_qa.py` 등 명시 소비 검사는 제외한 C #62의 고정 API/helper가 필요합니다. 기본 pytest 500 PASS를 이 명시 검사나 신규 SG01–16 전체 통과로 보고하지 않습니다.
- 보류 PR의 DG12·UnknownDocument 처리·선행 수정 누락, B 실제 Adapter 작업, G07 원인 검증·유료 모델 평가는 해결됐다고 표시하지 않습니다.
- 원격 병합·auto-merge·main 승격은 실행하지 않습니다. 기존 단계별 PR 병합/phase 승격은 이 후보와 새 리뷰 결과를 확인한 뒤 별도 진행해야 합니다.
