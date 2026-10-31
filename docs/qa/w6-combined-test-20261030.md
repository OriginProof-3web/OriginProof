# W6 합본 전체 시험 결과 (2026-10-30)

`phase/W6`(`5f7135b`)에 열린 PR **#102~#109** 8건을 로컬에서 병합한 상태(`46d782b`, 원격에 올리지 않음)로 CI(`quality-gate.yml`)와 같은 단계를 실행했습니다. 직접 실행 1회와, 독립된 두 팀(어벤져스·엑스맨)의 교차 실행 결과를 함께 적습니다.

## 결론

- 8건 모두 **충돌 없이 병합**됩니다. 병합 순서(first-parent): #102 → #104 → #103 → #105 → #106 → #107 → #108 → #109.
- CI와 같은 단계는 **모두 통과**했습니다. 실패한 단계는 없습니다.
- 다만 PR별 단독 실행과는 비교하지 않았습니다. 그래서 "병합에서만 생기는 문제가 없다"는 실행한 시험 범위 안에서만 말할 수 있습니다.

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
| c-recovery | 미실행 | `make` 없이 pytest 를 바로 부르면 analyzer import 실패, 경로를 맞추면 W6 2건·V5 7건 통과 |

c-recovery: `Makefile` 의 `WORKSPACE_PYTHONPATH` 에 `services/analyzer/src` 가 들어 있어 `make test-*-c-live`(CI와 같은 방법)로는 통과합니다. pytest 를 직접 부르면 #106 의 analyzer import 때문에 실패하니, 로컬에서는 `make` 로 실행해야 합니다.

## 실행 환경

macOS, colima Docker 29.5.2, uv, pnpm 11.19.0, forge 1.8.1, node 26.0.0. CI 고정값(forge v1.4.4, node 22.18.0)과 버전이 달라, 같은 결과를 보장하지는 않습니다. 각 PR의 CI는 따로 통과 상태입니다.

## 함께 발견한 위험 (후속)

- `fixtures/finals/test_v5_d_g07_runner.py:11-16` 은 부모 프로세스의 Git 환경변수(`GIT_DIR` 등)를 그대로 물려받습니다. `GIT_DIR` 이 잡힌 환경(예: Git hook 안)에서 돌리면 합성 커밋이 **실제 저장소에** 쓰입니다. 엑스맨 실행 중 로컬 복사본에서 실제로 일어났고, 원격에는 영향이 없었으며 복구했습니다. 하위 git 호출에서 `GIT_*` 변수를 지우도록 고치는 것을 제안합니다(D 담당).

## 남은 일

1. 각 PR 리뷰 승인 → `phase/W6` 병합 (#106 → #107 → #108 → #109 순서)
2. `phase/W6` → `integration` 승격
3. 미실행: Playwright E2E, 전체 Compose smoke, PostgreSQL opt-in 시험
