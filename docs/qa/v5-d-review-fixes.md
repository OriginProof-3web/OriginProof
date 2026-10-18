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
export PYTHONPATH="$PWD/services/analyzer/src:$C/apps/api/src:$C/packages/python:$C/services/indexer/src:$C/apps/api/tests"
"$C/.venv/bin/python" -m pytest -q -o addopts= fixtures/finals/v5_d_w2_governance_qa.py
"$C/.venv/bin/python" -m pytest -q -o addopts= fixtures/finals/v5_analysis_consumer_qa.py
```

W3/W4/분석 연결 PR에서는 그 head에 있는 `v5_d_w3_content_qa.py`, `v5_d_w4_lifecycle_qa.py`, `v5_d_analysis_integration_qa.py`를 첫 pytest 명령에 추가합니다. 생성 파일·공통 모델·C helper를 복제하거나 수동 수정하지 않습니다.

## 로컬 재검사

새 고정 C checkout의 첫 실행은 indexer import 경로 누락으로 collection ERROR였습니다. C의 기존 indexer 소스 경로도 명시하도록 CI/재현 명령을 수정했습니다. 수정 후 같은 새 환경에서 W2는 **12 PASS / 0 FAIL / 0 SKIP**입니다. consumer는 예상대로 **30 PASS / 1 FAIL(DG12)**이며 그대로 남겼습니다. workflow YAML 구문·명시 QA Ruff·diff 검사도 통과했습니다. GitHub CI 결과는 별도로 기록합니다.

W3 보강 후 W2+W3 **25 PASS / 0 FAIL / 0 SKIP**. 준비 단언의 첫 실행에서 CheckResult의 `field_path: null`과 버전이 포함된 canonical original의 검증 순서를 놓친 5개 실패를 수정했습니다. 버전 변조는 먼저 `STORED_CONTENT_MISMATCH/protected_fields`로 거부되며 C 제품은 변경하지 않았습니다.

W4 보강 후 W2+W3+W4 **30 PASS / 0 FAIL / 0 SKIP**. 구키 신규 서명은 정확히 `422 INVALID_SIGNATURE`로 거부됐고 전송 목록이 보존됐습니다. #72 새 GitHub stage도 12 PASS를 실행했으며 consumer는 DG12만 1 FAIL / 30 PASS였습니다.

## W5 평가 수정

실행 SHA `77e4f44198a16c12502283dade4db8b4289fb159`에서 관련 분석기 84 PASS, 전체 `make test` **329 PASS / 1 SKIP**입니다. skip은 indexer 실제 체인 opt-in 1개입니다. SDK transport/기한/취소·SQLite/합성 검사를 실제 환경 검사와 합산하지 않습니다. 설치 환경은 Python3.13.7/pytest8.4.2/OpenAI2.54.0이며 C 전용 QA 환경의 pytest9.1.1/FastAPI0.142.2와 구분합니다.

개발24개 재평가는 [결과 JSON](v5-d-development-evaluation.json)에 실행 SHA/평가 버전이 있습니다. 예전 `grounding_ratio=1.0`은 통과한 출력만의 불변식이어서 모델 후보 품질 점수로 사용할 수 없었습니다. 출력 안전성 범위와 후보 품질 NOT_EVALUATED를 분리하고, 거부된 보고서·기대 위치 분모/충족을 별도로 기록했습니다. 위험 예측과 원본/라벨/분할은 동일하며 유료/보류 평가는 실행하지 않았습니다. 후보 인용 정확도·누락률·위치 정확도의 실제 평가는 여전히 남습니다.

`make generate` 후 #80이 지정한 생성 Schema·TypeScript·OpenAPI·ABI·Solidity·Golden·합성 예시 diff가 없고 전체 Ruff가 통과했습니다. macOS 기본 make는 Xcode license shim으로 실행되지 않아 Command Line Tools PATH로 재실행했습니다. 공통 모델/lockfile 변경은 없습니다.

SDK 응답 helper는 기존 conftest의 pytest fixture로 옮겨 test 모듈 간 직접 import를 제거했습니다. `pytest --import-mode=importlib services/analyzer/tests`에서 **256 PASS**였고 기본 수집 모드도 전체 회귀로 확인합니다. `make typecheck`의 Python compileall·웹 tsc도 통과했습니다.

## 최종 D QA 후보

실행 소스 `b482875de7aa1014b7ef080b02950d7183b922b2`에서 명시 stage **42 PASS / 0 FAIL / 0 SKIP**(W2 12/W3 13/W4 5/분석 연결12), C lock 환경의 분석기 **256 PASS**입니다. 두 수치는 서로 다른 범위이며 기존 전체329 PASS에 합산하지 않습니다. `docs/portfolio/W5-D.md`의 양쪽 추가 기록 충돌은 과거 독립 QA/G07 기록과 이번 리뷰 수정 기록을 모두 보존해 해결했습니다. 동작/계약 충돌은 없었습니다.

현재 실제 GitHub 상태와 재리뷰 대상은 [리뷰 목록](../handoffs/v5_d_review_index.md)에 연결합니다. #72~#75 전용 stage가 실행됐고 consumer는 DG12만 실패했습니다. #76의 최종 CI는 push 후 PR Checks에서 별도로 확인합니다. 작성자 외 승인·실제 PostgreSQL/EVM/브라우저·유료 모델·보류36개·신규 통합 후보·단계 완료는 이번 재검사로 선언하지 않습니다.
