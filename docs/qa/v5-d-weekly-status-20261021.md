# D W1~W7 점검과 착수 결과 — 2026-10-21

> 2026-10-22 최신: D #72~#76은 팀에서 병합했고, B/C 검토를 근거로 G07을 로컬 legacy 범위 해결로 갱신했습니다. 병합 후953 PASS/opt-in11 SKIP. [정확한 SHA·검토·범위](v5-d-postmerge-20261022.md). 아래 이전 OPEN/미병합/리뷰 대기 문구는 당시 기록입니다. 사람 본인 확인·실제 신규 연결·단계 완료와 구분합니다.

> 최신 개발 완료 기록: 제한 모델 평가 실행기·수용 증거 도구·실제 로컬 독립 CLI 검증을 구현했습니다. G07은 fresh1/mixed5 각18 PASS, C 검토 전 OPEN입니다. [실행 SHA·검사·남은 인계](v5-d-development-completion-20261021.md). 아래 이전 미실행/미병합 표시는 당시 기록입니다.

> 2026-10-21 최신: 최신 추가 결과: #82/#86/#87 기준 반영, 100회 합성 성능·C63 고정 독립 검사와 G07 실제 fresh1/mixed3 반복. [현재 실행·수치·남은 작업](v5-d-performance-independent-20261021.md). 아래의 이전 SHA/미병합 표시는 당시 기록입니다.

기준은 계획서 **5.1**, 실제 D 소비 공통 계약 **v5-shared-0.2**입니다. `integration@1d9b349e4d8dbe697be0979dc51901827110fe5d`, `phase/W5@15c5588f9e96e2f530bb0e891c76af79b22a123c`와 최신 D 원격 `f42766e5a0818a6688ea7516782424c371c85d5a`를 확인했습니다. D 작업 브랜치 `codex/v5-d-independent-qa`를 정상 fast-forward했고 사용자 원본/보존 phase·기존 커밋은 유지했습니다. Wn은 개발 단계이며 달력 마감이 아닙니다.

## 전체 담당 작업

| 단계·작업 ID | 이미 구현·검사한 부분 | D의 남은 일 | 필요한 선행/담당 |
| --- | --- | --- | --- |
| W1 · V5-W1-D | 기존 안전성/fixture 재사용·공유 계약 소비 검사, #70/#71 병합 | 입력 종류/우선순위 결정, 합성60개 라벨/분할 A/C 리뷰 후 동결 | Q01·A/C |
| W2 · V5-W2-D | 기관 승인 실패 QA 12 PASS, #72 일반 PR | 실제 신규 기관 신청→2-of-3→재조회·긴급 정지와 기존 #51 브라우저 실패 재검사 | A/B/C 동일 후보·#85 seed/실제 Registry |
| W3 · V5-W3-D | 내용/DB 변조 QA 13 PASS, 이전65개 fixture/기여 기록 보존 | 실제 두 기관/템플릿 발행·QR·원본 bytes·기관 격리·v1/v2 회귀 | A 지갑/QR·B Adapter·C API/DB |
| W4 · V5-W4-D | 버전/키 QA 6 PASS; C 대행 추가 철회 이력 사례 포함 | 실제 동시 다음 버전·키 교체/사고·공동 복구·기존 consume 회귀 | B #68~#79·A/C 실제 연결 |
| W5 · V5-W5-D | 규칙/OpenAI adapter·원문 대조·D callback 12 PASS; 최종 gpt-6-luna 확정 | 선정 입력 실제 변환·원시 후보 근거 품질/누락/위치·실제 모델 평가·통합 웹 | Q01·유료 범위/예산·라벨/분할 리뷰 |
| W6 · V5-W6-D | 과거 fresh/mixed·clean 기록 보존; 현재 전체 회귀 684 PASS/10 SKIP | 동일 통합 SHA 수용표·G07 반복 재검사·성능·다른 장비·서비스 API 밖 검증·동결 차단표 | #86 phase 반영·A/B/C 통합·W5 승격 후 phase/W6 |
| W7 · V5-W7-D | 실행/제출 조건과 기존 인계 기록 확인 | 동일 RC 전체 리허설 3회·대체 장비/영상 전환·파일/링크/제출표 | 실행 RC·행사 조건·실제 통합 수용 결과 |

어느 단계도 mock/단위 성공만으로 단계 완료를 선언하지 않습니다. W1~W5 보완은 현재 열린 phase/W5로 모으고, W6 단계 생성/승격은 이전 phase의 integration 승격 뒤 C가 조율합니다. 과거 PR 전체를 재병합하거나 공유 phase에서 직접 개발하지 않았습니다.

## 이번에 먼저 처리한 작업

1. C가 D를 대행한 `d099808`의 같은 HEAD CI·필수 파일 manifest, 단계별 파일 추가(`597c4fb`, `22ec98a`, `f42766e`), `064891d`의 철회 이력 사례, W3-D의 과거65개 기여 기록 보존을 실제 코드와 대조했습니다. 같은 검증 source/lock에서 다시 실행했습니다. **Codex의 기술 대조·실행 기록이며 여인준 본인의 사실 확인/승인 코멘트는 아닙니다.** 대행자의 작성 이력을 보존했습니다.
2. 최신 리뷰에서 남은 테스트 수 감소·skip 은폐 방지를 구현했습니다. [JUnit 검사기](../../fixtures/finals/v5_d_junit_guard.py)는 W2 12/W3 13/W4 6/분석 연결12, consumer31의 파일별 정확 수·필수 module을 확인합니다. skip/failure/error·빈/손상 XML·중복 test ID·빠진 module·4파일 manifest 누락은 실패합니다. 새 경계 검사 16개가 통과했고 CI가 이를 먼저 실행합니다. 검사를 추가·제거할 때는 기대값을 함께 수정하고 리뷰해야 합니다. JUnit summary의 tests와 실제 testcase 수도 일치해야 합니다. 의미상 동일한 수로 다른 검사를 바꾸는 것까지 자동 판정하는 장치는 아닙니다.
3. stage/consumer의 JUnit artifact 이름에 실제 PR head SHA를 붙였습니다. [같은 HEAD workflow](../../.github/workflows/d-pinned-c-qa.yml)는 `contents: read`, 별도 secret 없이 mock/합성 범위로 실행합니다. 옛 고정 C `eaa0d16`을 현재 후보 대신 검사하지 않습니다. 재현 명령은 아래에 있습니다.
4. #84용 D 계약 소비 검토를 기록했습니다. 0.2의 실제 모델과 D의 validator/adapter/보관 callback을 대조했고 새 모델 사본이나 계약 변경 없이 실행했습니다. 이 문서는 작성자 외 승인·A/B 검토·이슈 체크 완료를 대신하지 않습니다.

## 공유 계약 0.2 D 소비 검토

- `AnalysisEvidence`: 빈 인용 거부, rule_id 1~100자, quote 최대500자, 코드 포인트 범위·source. D의 재검증과 겹친 반복 거부가 유지됩니다.
- `AnalysisReport`: evidence 최대50, limitations 최대20/각500자, 발행 검증 scope를 명시합니다. D `_AnalysisOutput`은 provider에서 verification=null로 좁히고 규칙/LLM 출처와 안전한 오류를 분리합니다.
- `AnalysisRequest.verification_session_id`: C가 만든 세션 참조를 C API가 소비합니다. D가 검증 세션·발행 판정을 만들어내지 않습니다. 실제 D callback을 넣은 분석 연결12개에서 위험/발행 독립, 세션 연결·원본/보고서 보관4조합·권한/늦은 결과를 검사했습니다.
- `AnalysisJob.error_code`: timeout/refusal/rate-limit/incomplete/schema 등 고정 안전 code를 소비하고 원시 provider 응답/입력을 로그에 남기지 않는 기존 회귀를 유지합니다.
- **검토 결론:** 현재 소비 범위의 mock/ASGI/SQLite 검사에서는 추가 수정 필요 사항이 발견되지 않았습니다. 모델 실제 품질·선정 입력 변환·실제 Registry/브라우저 연결과 타 담당자 승인은 미검증입니다. [공유 계약 검토 이슈 #84](https://github.com/OriginProof-3web/OriginProof/issues/84)에 인계할 기술 근거이며 인간의 소비 승인으로 기록하지 않습니다.

## 실제 검사와 범위

실행 코드 SHA: `e36e6ea2a0c93f1d4a199a73d993bcbfed2c2a5f`. 이후 문서 커밋/CI head와 구분합니다. Python3.13.7·pytest9.1.1·FastAPI0.142.2·OpenAI SDK2.54.0, 현재 lockfile 환경입니다.

| 검사 | 결과 | 범위/한계 |
| --- | --- | --- |
| `make test` | **684 PASS / 10 SKIP**, warning1 | 기존 API·core·분석기·indexer·CI 단위/합성. 실제 체인/PostgreSQL/프로세스 복구 opt-in은 미실행 |
| D stage 명시4파일 | **43 PASS / 0 SKIP** | W2 12/W3 13/W4 6/분석 연결12, ASGI/SQLite·합성 Registry·실제 ECDSA |
| D C-consumer | **31 PASS / 0 SKIP**, DG12 포함 | manifest30사례+계약 revision1. 과거 `30 PASS/1 FAIL`의 C 소스와 구분 |
| 분석기 경로+consumer | **352 PASS** | 분석기 경로321(기존 W3 코어 회귀65 포함)+consumer31, 위/전체 수와 중복 합산하지 않음 |
| 새 JUnit 보호 회귀 | **16 PASS** | 누락/감소/skip/실패/오류/중복/손상·정상 경계 |
| `make generate` | PASS·전체 생성 경로 diff 없음 | 원본 생성 모델/Schema/TS/OpenAPI/ABI/Golden·합성 예시 |
| Node Web Crypto 교차 hash | PASS, 두 템플릿 | 실제 브라우저/지갑 E2E 검사는 아님 |
| Ruff·workflow YAML/bash·diff | PASS | 기존/새 D 파일과 최소 권한 확인 |

```sh
UV_PROJECT_ENVIRONMENT=.uv-venv uv sync --all-packages --all-groups --locked
export PYTHONPATH="$PWD/services/analyzer/src:$PWD/apps/api/src:$PWD/packages/python:$PWD/services/indexer/src:$PWD/apps/api/tests"
.uv-venv/bin/python -m pytest -q --junitxml=stage.xml \
  fixtures/finals/v5_d_w2_governance_qa.py fixtures/finals/v5_d_w3_content_qa.py \
  fixtures/finals/v5_d_w4_lifecycle_qa.py fixtures/finals/v5_d_analysis_integration_qa.py
.uv-venv/bin/python fixtures/finals/v5_d_junit_guard.py stage.xml --suite stage
.uv-venv/bin/python -m pytest -q --junitxml=consumer.xml fixtures/finals/v5_analysis_consumer_qa.py
.uv-venv/bin/python fixtures/finals/v5_d_junit_guard.py consumer.xml --suite consumer
.uv-venv/bin/python -m pytest -q fixtures/finals/test_v5_d_junit_guard.py
```

최종 원격 head의 실제 stage/consumer XML은 PR #76의 `D same-head` 실행 artifact에 보관합니다. CI가 새로 통과하기 전에는 이 로컬 결과를 CI 결과라고 기록하지 않습니다.

## 남은 순서와 동결 차단

1. D #72~#76의 현 head 재리뷰, C 대행 변경에 대한 담당자 본인 사실 확인. Codex가 대신 사람의 확인 댓글/승인을 만들지 않습니다. #83·#64·#86·B 후속 등 선행 병합/대상 조율은 C가 진행하며 이번 작업은 원격 병합을 하지 않습니다.
2. Q01 입력 종류·우선순위, 유료 평가/전송 범위·예산, A/C의 합성60개 라벨/제안24·36 분할 리뷰. **최종 모델 `gpt-6-luna`는 이미 확정**됐습니다. Decisions API는 범위 밖입니다. 미정 입력을 지원으로 켜거나 보류36개로 튜닝하지 않습니다.
3. 같은 신규 A/B/C 후보에서 W2~W5 실제 지갑/브라우저/API/DB/체인 연결을 검사하고, #85 실행 패키지의 새/기존 합성 DB·재기동 설정을 독립 재현합니다. 아직 Registry 주입이 없는 seed/runbook을 실제 지갑 연결 완료로 표현하지 않습니다.
4. **G07은 미해결**입니다. #86은 원인/수정과 C의 반복 검사 근거를 제공하지만 아직 phase에 미반영입니다. 반영된 동일 후보에서 D의 mixed 반복 재검사 뒤 판정을 갱신합니다. 이번 DG12 통과와 합쳐 닫지 않습니다.
5. W6의 성능·선정 입력/실제 모델·다른 장비·서비스 API 밖 검증과 V5-F01~21을 모아 동결 차단 목록을 갱신합니다. 이후 W7 동일 RC 리허설3회·대체 영상·제출 조건/파일을 확인합니다. 해당 선행 없이 미래 통과/완료를 기록하지 않습니다.

[구조화 단계·수용표](v5-d-weekly-status-20261021.json), [현재 D 리뷰 목록](../handoffs/v5_d_review_index.md). 작성·검사: 사용자의 D 작업 지시에 따른 Codex. 작성자 외 리뷰/사람 라벨 승인/단계 승격은 후속입니다.


## 후속: 실행 중 발견한 의존성 보안 차단 해소

첫 새 CI `c943e7c`에서는 D stage43/consumer31·python-quality·contracts가 통과했으나, 공통 c-recovery가 `make security`의 Pillow8/certifi1 총9건으로 중단됐습니다. 실제 프로세스 복구는 이 감사 실패 뒤 실행되지 않았습니다.

D 전용 [보안 PR #87](https://github.com/OriginProof-3web/OriginProof/pull/87)을 `phase/W5@15c5588`에서 분리했습니다. Pillow12.3.0→13.0.0/certifi2026.7.22→2026.10.19 두 버전만 갱신하고 새 라이브러리는 추가하지 않았습니다. C의 공유 lock/major 갱신 리뷰는 대기입니다. 같은 보안 commit을 D QA에 정상 merge하여 중복 사본을 만들지 않았습니다.

- 보안 패치 실행 SHA `781b96ea9654a2bf277fa3adf38f9f4269bf46e1`: `make security` **0건**, phase 기반600 PASS/10 SKIP.
- 보안 수정 포함 D 실행 SHA `ffbf59e4388642458e7f092afca2228d694c621c`: 전체 **684 PASS/10 SKIP**, stage **43 PASS**, consumer **31 PASS**, JUnit 감소/skip 거부 통과.
- #87 CI에서는 의존성 감사와 실제 API 프로세스/폐기용 DB 복구 단계가 모두 통과했습니다. 이는 C의 기존 복구 시나리오이며 D의 G07 반복 재검사·새 지갑 E2E를 대신하지 않습니다.

[보안 근거·호환성·한계](v5-d-dependency-security-20261021.md). 사용자 원본을 수정하거나 source/lock 보안 검사를 완화하지 않았으며 원격 PR 병합·실제 모델 호출은 하지 않았습니다. W1~W7 단계 전체 완료가 아니라 지금 가능한 D 보완을 구현·검사·공유한 상태입니다.


## 후속: D PR 전파와 독립 PostgreSQL 재현

#72→#73→#74→#75→#76에 정확한 JUnit 수/summary·skip 보호와 `services/indexer/**`·`uv.lock` trigger를 merge로 전파했습니다. 단계 기대값은 12→25→31→31→43, consumer는 각31입니다. #75의 분석 연결 QA는 후속 #76 소유이므로 파일을 복제하지 않았습니다. #75에서 분석기321+consumer31=352 PASS를 별도 확인했습니다. #76 검사 소스 `babe3639eaf5b47aa0f621c2e41d09d7e6176d1e`에서 guard16 / stage43 / consumer31 PASS, 모두 skip0입니다. 이들은 이전 전체684/10skip 실행과 범위가 겹치며 합산하지 않습니다.

공통 모델·생성 경로·계약·lockfile·패키지 버전은 이번 후속에서 변경하지 않았습니다. #76 guard add/add 충돌은 기존 기능에 summary/정확 수 검증을 합쳤고, W5-D 추가 기록은 양쪽 기여를 유지했습니다. 계약/동작 판단이 필요한 충돌은 없었습니다.

#85 고정 소스의 실제 PostgreSQL seed/컨테이너 재생성 검사를 완료했습니다. [실행 근거와 readiness503 한계](v5-d-wallet-seed-live-20261021.md), [사람용 리뷰 초안·팀 요청](../handoffs/v5_d_human_review_drafts_20261021.md)을 확인합니다. G07은 #86 미병합으로 재검사 미실행이며 [후속 절차](v5-d-g07-retest-plan-20261021.md)만 준비했습니다. 담당자 대행 확인·외부 리뷰·새 Registry 연결·단계 완료는 대기입니다.


## 후속 개발: 후보 근거 지표와 G07 실행 도구

[새 개발 보고](v5-d-development-tools-20261021.md)에 원시 provider 후보를 grounding 전에 집계하는 평가0.3, 불변 후보/#86/phase/lockfile/clean 조건을 검증하는 G07 반복 도구를 구현·기록했습니다. 새 평가17개와 G07 단위27개, 전체 기본701 PASS/기존10 SKIP, stage43/consumer31 PASS입니다. 기존684 PASS 기록과 중복 합산하지 않습니다. 제어된 합성 replay는 scorer 검사이며 실제 모델 평가가 아닙니다. 실제 G07은0회·OPEN, 입력 선정/유료 평가/라벨 리뷰·실제 Registry/브라우저 연결과 단계 완료는 여전히 후속입니다.
