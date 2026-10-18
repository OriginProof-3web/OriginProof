# D 리뷰 수정과 고정 C QA

2026-10-18, 계획서 5.1 / 병합 공통 계약 v5-shared-0.1 기준입니다. D W2 준비 브랜치부터 최신 `integration@54705588d660aceea71ff1cb03eefb5aefe37aa4`(#80 포함)를 merge로 반영하고, 뒤 단계에는 D 선행 브랜치를 순서대로 merge합니다. 과거 phase·병합된 #70/#71·타 담당 제품을 수정하지 않습니다. PR 대상 변경/단계 승격은 C 조율 후 별도입니다.

## 실행 경계

기존 Quality Gate의 기본 pytest에는 C v5 모듈을 요구하는 D 명시 QA가 포함되지 않습니다. 새 `.github/workflows/d-pinned-c-qa.yml`은 PR head와 C #62 고정 소스 `eaa0d166269833cf7ee49675cfa777b0208c3725`를 **별도로** checkout하고 C lockfile 환경에서 실행합니다. D analyzer를 먼저 import하고 C API·공통 모델·fixture를 재사용합니다. C 후보 v5-shared-0.2 소비 실험이며 병합 계약 또는 실제 연결 완료가 아닙니다.

- trigger: D 명시 QA·분석기·workflow·consumer manifest를 바꾸는 pull_request.
- 권한: contents read. 별도 서비스/API secret 불필요, 유료 모델 0회. 합성 소켓 차단 fixture를 유지합니다.
- `stage`: 해당 D 단계 head에 존재하는 W2/W3/W4/분석 연결 파일을 **명시 실행**합니다. 예상 개수는 단계별 12/25/30/42입니다. 빈 목록은 실패합니다.
- `consumer`: 병합된 W1의 `v5_analysis_consumer_qa.py` 31개를 별도 실행합니다. C의 **DG12 겹친 인용 미해결** 때문에 고정 C에서 30 PASS / 1 FAIL이 예상됩니다. 실패를 skip/xfail/continue-on-error로 바꾸지 않았으므로 이 check는 수정된 C 소비 전까지 실패할 수 있습니다. 녹색 stage와 합쳐 전체 통과로 보고하지 않습니다.
- 실제 GitHub 실행 결과는 PR Checks와 JUnit artifact를 확인합니다. 로컬 ASGI/SQLite/합성 Registry 결과는 실제 PostgreSQL/EVM/브라우저·유료 OpenAI 검사가 아닙니다. G07은 계속 미해결입니다.

## 같은 명령으로 재현

저장소 밖에 C SHA를 checkout한 뒤 D 작업 루트에서 실행합니다. `$C`는 해당 checkout의 절대 경로입니다.

```sh
uv sync --project "$C" --all-packages --all-groups --locked
export PYTHONPATH="$PWD/services/analyzer/src:$C/apps/api/src:$C/packages/python:$C/apps/api/tests"
"$C/.venv/bin/python" -m pytest -q -o addopts= fixtures/finals/v5_d_w2_governance_qa.py
"$C/.venv/bin/python" -m pytest -q -o addopts= fixtures/finals/v5_analysis_consumer_qa.py
```

W3/W4/분석 연결 PR에서는 그 head에 있는 `v5_d_w3_content_qa.py`, `v5_d_w4_lifecycle_qa.py`, `v5_d_analysis_integration_qa.py`를 첫 pytest 명령에 추가합니다. 생성 파일·공통 모델·C helper를 복제하거나 수동 수정하지 않습니다.

## 로컬 재검사

수정된 W2 파일은 새 고정 C checkout/lockfile 환경에서 **12 PASS / 0 FAIL / 0 SKIP**입니다. workflow YAML 구문·명시 QA Ruff·diff 검사도 통과했습니다. GitHub CI 결과는 별도로 기록합니다.
