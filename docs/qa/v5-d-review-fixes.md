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

W3 보강 후 W2+W3 **25 PASS / 0 FAIL / 0 SKIP**. 준비 단언의 첫 실행에서 CheckResult의 `field_path: null`과 버전이 포함된 canonical original의 검증 순서를 놓친 5개 실패를 수정했습니다. 버전 변조는 먼저 `STORED_CONTENT_MISMATCH/protected_fields`로 거부되며 C 제품은 변경하지 않았습니다.

W4 보강 후 W2+W3+W4 **30 PASS / 0 FAIL / 0 SKIP**. 구키 신규 서명은 정확히 `422 INVALID_SIGNATURE`로 거부됐고 전송 목록이 보존됐습니다. #72 새 GitHub stage도 12 PASS를 실행했으며 consumer는 DG12만 1 FAIL / 30 PASS였습니다.

## W5 평가 수정

실행 SHA `77e4f44198a16c12502283dade4db8b4289fb159`에서 관련 분석기 84 PASS, 전체 `make test` **329 PASS / 1 SKIP**입니다. skip은 indexer 실제 체인 opt-in 1개입니다. SDK transport/기한/취소·SQLite/합성 검사를 실제 환경 검사와 합산하지 않습니다. 설치 환경은 Python3.13.7/pytest8.4.2/OpenAI2.54.0이며 C 전용 QA 환경의 pytest9.1.1/FastAPI0.142.2와 구분합니다.

개발24개 재평가는 [결과 JSON](v5-d-development-evaluation.json)에 실행 SHA/평가 버전이 있습니다. 예전 `grounding_ratio=1.0`은 통과한 출력만의 불변식이어서 모델 후보 품질 점수로 사용할 수 없었습니다. 출력 안전성 범위와 후보 품질 NOT_EVALUATED를 분리하고, 거부된 보고서·기대 위치 분모/충족을 별도로 기록했습니다. 위험 예측과 원본/라벨/분할은 동일하며 유료/보류 평가는 실행하지 않았습니다. 후보 인용 정확도·누락률·위치 정확도의 실제 평가는 여전히 남습니다.

`make generate` 후 #80이 지정한 생성 Schema·TypeScript·OpenAPI·ABI·Solidity·Golden·합성 예시 diff가 없고 전체 Ruff가 통과했습니다. macOS 기본 make는 Xcode license shim으로 실행되지 않아 Command Line Tools PATH로 재실행했습니다. 공통 모델/lockfile 변경은 없습니다.

SDK 응답 helper는 기존 conftest의 pytest fixture로 옮겨 test 모듈 간 직접 import를 제거했습니다. `pytest --import-mode=importlib services/analyzer/tests`에서 **256 PASS**였고 기본 수집 모드도 전체 회귀로 확인합니다. `make typecheck`의 Python compileall·웹 tsc도 통과했습니다.
