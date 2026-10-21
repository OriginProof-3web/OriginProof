# D 리뷰 수정과 동일 HEAD QA

2026-10-21 기준 계획서 5.1 / 공통 계약 v5-shared-0.2입니다. C phase/W5 코드는 각 D PR head에 이미 포함돼 있으며, QA와 API·코어·indexer를 **동일 HEAD**에서 실행합니다. 과거 C SHA를 별도 checkout하거나 소스를 섞지 않습니다. 아래 과거 기록은 당시 실행 근거로만 보존합니다.

## 현재 실행 경계

- `.github/workflows/d-pinned-c-qa.yml`은 PR head SHA를 checkout하고 해당 lockfile로 설치합니다. `apps/api/**`, `packages/python/**`, `services/analyzer/**`, `services/indexer/**`, `uv.lock`과 D QA/guard/manifest 변경이 trigger입니다.
- stage manifest의 필수 파일과 JUnit testcase·summary를 검증합니다. 단계 누적 기대값은 #72 W2=12, #73 W2+W3=25, #74/#75 W2+W3+W4=31(철회 후 과거 비활성 회귀 포함), #76 분석 연결까지=43입니다. consumer는 별도 31입니다. failures/errors/skips=0이어야 하며 개수 변경은 기대값과 함께 리뷰해야 합니다.
- JUnit은 `d-same-head-<suite>-<head SHA>` artifact로 보존합니다. CI 결과는 현재 PR Checks를 확인하고 로컬 결과와 구분합니다. C의 DG12 겹친 인용 수정이 포함돼 consumer 31개가 통과하는 기준입니다.
- ASGI·SQLite·합성 Registry·mock/SDK transport 검사입니다. 실제 PostgreSQL·EVM·브라우저·유료 모델·입력 선정·G07 해결·단계 완료를 뜻하지 않습니다. B #68 Foundry 회귀와 D 합성 Registry QA는 별개입니다.
- AI(Codex)가 기술 검증·workflow·문서를 보완했습니다. 사람의 대행 변경 확인·작성자 외 승인을 대신하지 않습니다.

## 같은 HEAD에서 재현

```sh
UV_PROJECT_ENVIRONMENT=.uv-venv uv sync --all-packages --all-groups --locked
export PYTHONPATH="$PWD/services/analyzer/src:$PWD/apps/api/src:$PWD/packages/python:$PWD/services/indexer/src:$PWD/apps/api/tests"
.uv-venv/bin/python -m pytest -q -o addopts= --junitxml=stage.xml $(sed '/^#/d; /^$/d' fixtures/finals/v5_d_stage_qa_files.txt)
.uv-venv/bin/python fixtures/finals/v5_d_junit_guard.py stage.xml --suite stage
.uv-venv/bin/python -m pytest -q -o addopts= --junitxml=consumer.xml fixtures/finals/v5_analysis_consumer_qa.py
.uv-venv/bin/python fixtures/finals/v5_d_junit_guard.py consumer.xml --suite consumer
```

환경 fingerprint·소스 SHA와 JUnit을 함께 보존합니다. 보안 PR #87은 phase/W5에서 리뷰 대기 중이며, 이전 lockfile의 보안 감사 결과는 D 기능 검사와 별도로 보고합니다.

## 과거 실행 기록 (2026-10-18, 당시 별도 C 소스 조합)

다음 수치는 과거 소스 조합의 기록이며 현재 재현 명령이나 현재 통과 판정이 아닙니다.

## 로컬 재검사

새 고정 C checkout의 첫 실행은 indexer import 경로 누락으로 collection ERROR였습니다. C의 기존 indexer 소스 경로도 명시하도록 CI/재현 명령을 수정했습니다. 수정 후 같은 새 환경에서 W2는 **12 PASS / 0 FAIL / 0 SKIP**입니다. consumer는 예상대로 **30 PASS / 1 FAIL(DG12)**이며 그대로 남겼습니다. workflow YAML 구문·명시 QA Ruff·diff 검사도 통과했습니다. GitHub CI 결과는 별도로 기록합니다.
