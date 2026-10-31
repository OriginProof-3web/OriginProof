# W6 합본 전체 시험 결과 (2026-10-30)

> 2026-10-31 정정: 통과 범위, 복구 시험 실패 원인, PR별 CI 문구를 바로잡았습니다. 시험 수치는 바꾸지 않았습니다.

`phase/W6`(`5f7135b`)에 열린 PR **#102~#109** 8건을 로컬에서 병합한 상태(`46d782b`, 원격에 올리지 않음)로 CI(`quality-gate.yml`)와 같은 단계를 실행했습니다. 직접 실행 1회와, 독립된 두 팀(어벤져스·엑스맨)의 교차 실행 결과를 함께 적습니다.

## 결론

- 8건 모두 **충돌 없이 병합**됩니다. 병합 순서(first-parent): #102 → #104 → #103 → #105 → #106 → #107 → #108 → #109.
- 아래 표에 적은 단계는 **모두 통과**했습니다. CI의 **Playwright E2E와 D 검증 작업은 직접 실행하지 않았으므로** CI 전체 통과라는 뜻이 아닙니다(D 검증 220건은 엑스맨 보고값입니다).
- 다만 PR별 단독 실행과는 비교하지 않았습니다. 그래서 "병합에서만 생기는 문제가 없다"는 실행한 시험 범위 안에서만 말할 수 있습니다.
- **시험 통과가 결함이 없다는 뜻은 아닙니다.** 이후 검사에서 시험이 잡지 못한 결함이 나왔습니다. 승인 없는 issuer 가입(#109로 유입, #119), 조회 중 새 블록으로 인한 INCONCLUSIVE(#119), 전체 구간 조회(#120), 금액 입력 처리(#118)입니다.

## 직접 실행 (make·uv, CI 순서 그대로)

| 단계 | 결과 |
|---|---|
| `uv sync --all-packages --all-groups --locked` | ✅ |
| `validate_structure.py` | ✅ finals-v3 |
| 생성물 최신성 (`make generate` + `git diff --exit-code`) | ✅ |
| `pytest` | ✅ 1424 passed, 19 skipped |
| `ruff check apps packages services scripts` | ✅ (아래 주 1) |
| `compileall` | ✅ |
| web-v5 `node --test` | ✅ 127 pass, 5 skipped, 0 fail |
| demo-web lint · typecheck · test(8) · build | ✅ |
| `forge test` (OZ v5.7.0, forge-std v1.16.2) | ✅ 101 passed |
| `make security` | ✅ No known vulnerabilities |
| `make test-w6-c-live` | ✅ 2 passed |
| `make test-v5-c-live` | ✅ 7 passed |

주 1: `forge install` 로 받은 `packages/contracts/lib/**/forge-std/scripts/vm.py` 에서 26건이 걸립니다. 이 폴더는 CI의 python-quality 작업에는 없는 외부 코드라 제외하고 검사했고, 제외하면 통과합니다. 같은 저장소에서 계약 시험과 ruff를 함께 돌리는 경우를 대비해 `ruff` 설정에 `packages/contracts/lib` 제외를 넣는 것을 제안합니다.

## 팀 교차 실행

| 항목 | 어벤져스 | 엑스맨 |
|---|---|---|
| pytest | 미실행(의존성 설치 금지 조건) | 1424 passed, 19 skipped |
| forge | 101 passed | 101 passed |
| D 전체 검증 | 미실행 | 220 passed |
| 생성물 비교 | — | 27개 파일 일치 |
| web-v5 | 127 pass, 5 skipped | 127 pass, 5 skipped |
| demo-web lint·typecheck·test·build | 미실행 | 통과(test 8) |
| c-recovery | 미실행 | 처음에는 analyzer import 실패, 경로를 우회하면 W6 2건·V5 7건 통과(CI와 같은 조건 아님) |

c-recovery: 복구 시험의 API 프로세스는 자기 `PYTHONPATH`에 `services/analyzer/src`를 넣지 않습니다(`scripts/ci/test_w6_c_recovery.py:71-76`). 그래서 `make` 여부가 아니라, 가상환경의 설치 경로로 분석기를 찾을 수 있는지가 결과를 가릅니다. iCloud 데스크톱 폴더의 복사본에서는 `.uv-venv` 안 `.pth` 파일에 숨김 표시가 붙어 있었고, 2026-10-31 재실행 때 `make`로도 분석기 import가 실패해 W6·V5가 전부 실패했습니다. 숨김 표시를 풀어도 다시 붙었고, iCloud 밖의 새 복사본에서는 같은 합본이 W6 2건·V5 7건 통과했습니다. 2026-10-30 실행이 같은 폴더에서 통과한 이유는 확인하지 못했습니다.

## 실행 환경

macOS, colima Docker 29.5.2, uv, pnpm 11.19.0, forge 1.8.1, node 26.0.0. CI 고정값(forge v1.4.4, node 22.18.0)과 버전이 달라, 같은 결과를 보장하지는 않습니다. 이 문서를 처음 쓸 때 적은 "각 PR의 CI는 따로 통과"는 8건 모두를 확인한 내용이 아니어서 뺐습니다.

## 함께 발견한 위험 (후속)

- `fixtures/finals/test_v5_d_g07_runner.py:11-16` 은 부모 프로세스의 Git 환경변수(`GIT_DIR` 등)를 그대로 물려받습니다. `GIT_DIR` 이 잡힌 환경(예: Git hook 안)에서 돌리면 합성 커밋이 **실제 저장소에** 쓰입니다. 엑스맨 실행 중 로컬 복사본에서 실제로 일어났고, 원격에는 영향이 없었으며 복구했습니다. 하위 git 호출에서 `GIT_*` 변수를 지우도록 고치는 것을 제안합니다(D 담당).

  → #113에서 `git_environment()`로 `GIT_` 변수를 지우도록 고쳐졌습니다(`fixtures/finals/v5_d_g07_runner.py:36-38`).

## 남은 일

이 문서를 쓴 뒤 #103, #106~#109가 병합됐습니다. 지금 남은 일은 다음과 같습니다.

1. #118, #119, #120에 적은 결함 수정
2. 열린 PR(#102, #104, #105, #114, #115, #116) 처리
3. `phase/W6` → `integration` 승격
4. 미실행: Playwright E2E, 전체 Compose smoke, PostgreSQL opt-in 시험
