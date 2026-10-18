# V5 C·B·D 머지 전 통합 검증 — 2026-10-17

> 최신 상태는 문서 마지막의 “2026-10-18 #68 철회 상태 보존 반영” 절입니다. 앞선 검사·미완료 목록은 해당 SHA 시점의 기록입니다.

이 문서는 사용자가 승인 추천 대상으로 지정한 12개 PR을 함께 적용할 때의 충돌 해결과 검증 근거입니다. 검증용 Draft 후보이며 단계 완료·실제 신규 지갑 연결·integration 병합을 뜻하지 않습니다.

## 기준과 포함 범위

- 담당: C `@Jordi2801K`의 통합 조율. 사용자가 승인한 범위에서 Codex가 충돌 해결·검사·기록을 수행했습니다. 다른 팀원의 구현·저자·사람 리뷰를 대신 주장하지 않습니다.
- 브랜치: `codex/v5-premerge-cbd`; 시작 `integration@33bc4f4e7456c5ef7c2df8c8bf09f8014e0169f8`.
- 공용 소스·Contract·웹·실제 복구 검증 SHA: `f68799f88e75256ddaec4e19580e4430da4e27b2`. 최초 문서 head `4041ea484c654db43faca03b8283cff48081ff7a`의 CI에서 실행 의존성 누락을 발견했습니다.
- 의존성 수정·Python 재검증 SHA: `1d26f1043b3bc0fe9168c41f5c417ed0b08298aa`. 이 수정은 API/root 의존성 선언과 lock 메타데이터만 바꾸며 소스·Contract·웹·생성물은 동일합니다. 이후 보고서·구조화 근거·C 기여 기록만 갱신합니다.
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
| 개발 의존성 없는 API 전용 환경 | PASS | pytest/respx 없이 API·두 Reader·Writer import, OpenAPI 및 전체 생성 명령 성공. |
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
UV_FROZEN=1 UV_NO_DEV=1 UV_PYTHON=3.13.0 make generate UV_ENV=build/premerge/api-runtime-venv
```

실제 복구 명령은 Docker와 고정 Foundry·Contract 라이브러리가 있는 폐기 가능한 합성 환경에서만 실행합니다. 기존 Compose/DB 볼륨은 사용하지 않았고, 검사에서 만든 컨테이너와 웹 서버가 종료됐음을 확인했습니다. 로컬 원시 로그/JUnit은 ignored `build/premerge/`, 지속되는 요약은 [구조화 근거](v5_premerge_cbd.json)입니다.

환경: macOS arm64, Python 3.13.0, uv 0.12.1, Node 22.14.0, corepack pnpm version 조회 11.19.0 / 의존성 설치 출력 11.25.0, Foundry 1.4.4, solc 0.8.26. Contract 라이브러리는 OpenZeppelin v5.7.0 / forge-std v1.16.2 고정 SHA를 사용했습니다. 원격 CI의 Linux/Node 22.18.0/uv 0.8.17 환경 재현은 PR의 새 검사 결과로 따로 확인합니다.

오프라인 uv/pnpm 설치는 패키지·레지스트리 메타데이터 캐시 부족으로 처음 실패했고, 고정 버전 그대로 온라인 재시도해 설치·정책 검사를 완료했습니다. Python 테스트의 기존 Starlette httpx deprecation 경고와 웹의 기존 CSS autoprefixer 경고가 있었으며 기능 검사는 통과했습니다.

최초 [CI 실행](https://github.com/OriginProof-3web/OriginProof/actions/runs/38938875066)은 Contract·실제 복구 작업이 통과했지만 API 생성 명령에서 `ModuleNotFoundError: eth_abi`로 실패했습니다. B의 Legacy Reader를 공용 export에 보존하면 API import에도 eth-abi가 필요하지만 root dev에만 선언돼 있었기 때문입니다. 기존 버전 그대로 API 실행 의존성으로 옮기고 lock을 재생성했습니다. 개발 패키지가 없는 별도 환경에서 Makefile의 PYTHONPATH를 사용한 API import/OpenAPI/전체 생성 및 생성물 무변경을 확인하고 Python 500 PASS/8 SKIP을 재확인했습니다. 패키지 버전·애플리케이션 로직은 바꾸지 않았습니다.

## 남은 검토와 범위

- 이 통합 후보 자체의 작성자 외 리뷰는 아직 없습니다. 원 PR의 승인 결과가 새 통합 후보의 승인으로 이전된 것으로 기록하지 않습니다.
- 원래 C #57/#58은 작성자 본인 승인 불가로 다른 팀원의 확인이 남아 있습니다.
- 원 PR을 개별 병합하는 경우에도 이 후보의 `1d26f1043b3bc0fe9168c41f5c417ed0b08298aa` 실행 의존성 수정을 함께 반영해야 합니다. 원 PR head 자체는 이번에 변경하지 않았습니다.
- 실제 신규 WalletRegistry Adapter ↔ 신규 C API/DB ↔ A 지갑 화면 ↔ D 분석기의 연결 검증은 이번 범위 밖입니다. 현재 후보의 실제 2개 복구 검사는 이전 호환 경로입니다.
- D의 `fixtures/finals/v5_d_w2_governance_qa.py` 등 명시 소비 검사는 제외한 C #62의 고정 API/helper가 필요합니다. 기본 pytest 500 PASS를 이 명시 검사나 신규 SG01–16 전체 통과로 보고하지 않습니다.
- 보류 PR의 DG12·UnknownDocument 처리·선행 수정 누락, B 실제 Adapter 작업, G07 원인 검증·유료 모델 평가는 해결됐다고 표시하지 않습니다.
- 원격 병합·auto-merge·main 승격은 실행하지 않습니다. 기존 단계별 PR 병합/phase 승격은 이 후보와 새 리뷰 결과를 확인한 뒤 별도 진행해야 합니다.


## 2026-10-18 C 리뷰 보완 후 후보 재검증

검증 후보 코드: `c8584ecb219db1c2773acb451a6974c262bdc4a8`. C #57·#59~#63의 보완과 공식 integration
`5470558`(#80), D #72~#74의 최신 리뷰 보완 `a9ada27`을 원래 커밋 이력대로
포함했습니다. B #69/#78/#79와 D #75/#76은 이 후보에 추가하지 않았습니다.

C 수정은 이메일 HMAC/만료 정리·REACTIVATE ABI, 정확한 REVOKED 확정,
SUPERSEDED 거부 HTTP 회귀, DG12 겹침 인용, wallet 전용 보관 정리, 독립 RPC의
정확한 not-found 분류, projection revision 재현성과 레거시 기관 ID 충돌 검사입니다.
계획서와 재사용 인계의 충돌 중 누락한 본문은 복원했고 모든 C branch에서 계획
14~16장과 재사용 기록이 유지되는지 확인했습니다. B/D 기여 기록도 보존했습니다.

| 최종 로컬 검사 | 결과·범위 |
| --- | --- |
| 후보 기본 전체 Python | 622 PASS / 15 opt-in SKIP / 기존 Starlette 경고 1건 |
| D 명시 소비 QA 네 파일 | 61 PASS. ASGI/SQLite/합성 Registry, 실제 모델·EVM 검사 아님 |
| Foundry 전체 offline | 100 PASS / 0 FAIL / 0 SKIP. 알려진 #68 결함의 새 회귀는 포함하지 않음 |
| 기존 실제 복구 | 2 PASS. 임시 PostgreSQL·Anvil·실제 API 프로세스 |
| 신규 실제 복구 | 6 PASS. 임시 PostgreSQL·실제 API 프로세스, Registry/분석기는 합성 |
| 생성물·Node hash | 다섯 생성기 무변경, 두 템플릿 hash 교차 검사 PASS |
| 정적 검사 | Ruff·구조·diff PASS |

D 소비 검사는 수정된 후보와 같은 head SHA를 별도 고정 checkout하여 실행하도록
후보의 CI를 바꿨습니다. 과거 C `eaa0d16`을 대상으로 한 D 원 PR의 별도 CI 실패를
후보 PASS로 덮어쓰지 않습니다. 로컬 첫 수집은 C 전용 환경에 B의 eth-abi가 없어
실패했고, 후보 lock에 맞춰 `.venv`를 동기화한 뒤 네 파일을 실제 실행했습니다.
Contract 첫 시도는 라이브러리 부재로 실패했으며 기존 고정 OpenZeppelin v5.7.0 /
forge-std v1.16.2를 설치한 뒤 100 PASS를 확인했습니다. 새 의존성은 추가하지 않았습니다.

웹/브라우저 검사는 이번에 다시 실행하지 않았습니다. B #68의 철회 상태 유지 결함,
실제 B port/배포·A 지갑·D 모델 연결, shared 0.2 소비자 리뷰, G07과 유료 평가는
여전히 남습니다. 기본 Contract 검사 통과가 해당 결함 해결·통합 RC·단계 완료를 뜻하지
않으며 승인/리뷰 상태를 변경하거나 원격 PR을 병합하지 않습니다.

원격 공유: 최초 push는 자동 승인 검토 서비스의 사용 한도 초과로 실행되지 않았습니다.
이는 안전성 거절이 아닌 검토 서비스 실패이며 로컬 커밋/검사 결과는 보존돼 있습니다.
후속 재시도는 정상 승인 검토를 통과했고 C #57·#59~#63 및 #77의 자기 브랜치를
일반 push했습니다. 기존 PR 리뷰/병합 상태는 유지하며 새 head의 원격 CI는 확인 중입니다.


## 2026-10-18 #68 철회 상태 보존 반영

사용자님의 #68/#77 수정 지시에 따라 B 수정 `2d1df07bd48c54c04d22ce20ac1ee3725316e878`을 후보에 일반 merge했습니다.
검증 코드 SHA는 `07791099cfbcdec21b40b6bb2c00515579457080`이며 뒤의 기록 커밋은 문서만 변경합니다. 이전 후보의
“#68 철회 상태 유지 결함” 보류 사유는 이 보완으로 해소됐고 작성자 외 재리뷰는 남습니다.
다른 B/D 후속 PR과 기존 phase/integration/main은 수정·병합하지 않았습니다.

publish는 이전 최신의 저장 state가 ACTIVE(1)인 경우에만 SUPERSEDED(3)와 대체 이벤트를
적용합니다. 이미 REVOKED(2)인 버전은 전체 snapshot을 보존하며 새 버전의 발행 이벤트·
최신 포인터·nonce만 정상 반영합니다. 새 nonce로 구버전을 다시 철회하면
DocumentAlreadyRevoked이며 nonce와 두 버전은 불변입니다. 정상 SUPERSEDED 버전의
첫 철회는 계속 허용합니다. 공유 명세·ADR·개발 계획·B 인계를 같은 조건으로 맞췄습니다.

| 재검증 | 결과·실제 범위 |
| --- | --- |
| #68 수정 전 새 회귀 | FAIL: 재철회가 거부되지 않음을 실제 EVM 검사로 재현 |
| #68 수정 후 Foundry 전체 | 89 PASS / 0 FAIL / 0 SKIP |
| #77 Foundry 전체 | 101 PASS / 0 FAIL / 0 SKIP, fuzz 각512회 |
| #77 전체 Python | 622 PASS / 15 opt-in SKIP / 기존 Starlette 경고1 |
| #77 D 소비 QA 네 파일 | 61 PASS, ASGI/SQLite/합성 Registry |
| #77 실제 복구 | 8 PASS = 기존2(PostgreSQL/Anvil/프로세스) + 신규6(PostgreSQL/프로세스·합성 Registry/분석기) |
| ABI·생성·정적 검사 | 컴파일 전체 ABI 동일, 다섯 생성기 diff 없음, 두 템플릿 Node hash·Ruff·구조·Solidity format·diff PASS |

실행 명령은 기존 환경에서 `forge test --offline`, 전체 `pytest -q`, 명시 D 네 파일,
`W6_C_LIVE_TEST=1 V5_C_LIVE_TEST=1 ... pytest -q scripts/ci/test_w6_c_recovery.py
scripts/ci/test_v5_c_recovery.py`, `UV_FROZEN=1 UV_OFFLINE=1 make generate UV_ENV=.venv`입니다.
개인 사용자 DB/체인 대신 검사 전용 자원을 만들고 정리했습니다. 의존성/lockfile·ABI·
EIP-712/domain·Golden·storage 선언 변경은 없습니다. 실제 배포는 실행하지 않았으며,
비업그레이드 계약의 기존 주소가 이 수정으로 바뀌지는 않습니다.

B #69/#78/#79에 이 수정은 아직 forward 반영하지 않았습니다. #78의 기존 대조 로직은
철회/대체 상태(2/3)를 허용하지만 새 Contract 기준의 기대값과 실제 연결은 해당 PR에서
재검증해야 합니다. D #72~#76 원본 CI의 이전 C SHA pin, 실제 B/A/D 연결·G07·유료 평가,
shared 0.2 소비자 리뷰와 단계 수용은 계속 별도입니다. 리뷰 승인·Draft·base·원격 merge는
변경하지 않습니다. 새 원격 head의 CI는 push 뒤 확인합니다.
