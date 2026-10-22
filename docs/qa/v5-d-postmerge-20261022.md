# D 병합 후 검증·G07 범위 판정 — 2026-10-22

계획서5.1 / v5-shared-0.2. 팀에서 D #72~#76과 B #78/#79, C #85를 병합한 뒤 phase/W5 `f6e7fdb6727f6b7957d8acc7f3e0bf7e7674ea5f`에서 별도 D `codex/v5-d-postmerge-qa`를 만들었습니다. 기존 branch/커밋·사용자 원본·보존 phase를 유지했습니다. 공유 phase에서 직접 개발하지 않았으며 이 작업이 PR 병합이나 승격을 실행한 것은 아닙니다. [구조화 결과](v5-d-postmerge-20261022.json).

## 병합·리뷰와 기존 개발 결과

#76 최종 head9270a84는 2026-10-22 09:21:42 KST에 be93c7f로 병합됐습니다. [대표의 같은 HEAD 승인](https://github.com/OriginProof-3web/OriginProof/pull/76#pullrequestreview-5607814995)을 확인했습니다. 제한 평가 실행기·0600 journal/중단재개·수용 증거 도구·실제 독립 로컬 검증과 첫 하네스 실패/수정 이력은 [원래 개발 보고](v5-d-development-completion-20261021.md)에 보존합니다. 실제 EVM/CLI 실행5b50ac4 및 G07의 기존 두 제품 SHA를 이번 phase 실행 SHA로 바꾸지 않습니다.

[최종 D CI](https://github.com/OriginProof-3web/OriginProof/actions/runs/39591674050)의 artifact를 내려받아 stage43/consumer31/성능16/독립71(C49+D22), failure/error/skip0을 확인했습니다. [최종 Quality Gate](https://github.com/OriginProof-3web/OriginProof/actions/runs/39591674030)는 Python788 PASS/기존 opt-in10 SKIP, 보안 감사0건, 실제 폐기 DB/API 복구2 PASS, Foundry/웹/생성물 검사 통과입니다. 원래 #76의6종 CI와 병합 뒤 Discord 통지는 다른 항목입니다.

## 병합 후 같은 phase 검사

| 검사 | 실제 결과·범위 |
| --- | --- |
| 기본 전체 Python | **953 PASS / opt-in11 SKIP / 기존 Starlette 경고1** |
| supporting 수용 도구 | stage43/consumer31/성능16/D독립22 PASS, skip0, source_consistent=true |
| 별도 D guard/G07·수용 도구·고정 C63 | **124 PASS** =16+27+10+D22+C49 |
| make generate·Ruff·diff | PASS / 생성물 차이 없음 |

기본11 SKIP은 기존 opt-in10개에 이번 phase에 병합된 B의 `test_wallet_live.py` 일회용 EVM 검사가 추가된 것입니다. 통합 범위가 늘어난 결과이며 D 필수 검사 누락/skip 허용으로 바꾸지 않았습니다. supporting 도구는 실제 수용 BLOCKED/exit2를 유지하며 W1~W7 완료를 선언하지 않습니다. 겹치는 수를 합산하지 않습니다.

별도 도구 첫 명령에서 macOS 기본 Git shim이 선택돼 G07 단위27개가 setup error였고 나머지97개는 통과했습니다. 설치된 Command Line Tools PATH로 해당27개만 다시 실행해 통과했습니다. Xcode 라이선스/시스템 설정이나 코드를 바꿔 우회하지 않았습니다. 실제 G07 fresh/mixed 실패가 아닙니다.

## G07: 로컬 legacy 범위 해결

**판정: RESOLVED_LOCAL_LEGACY.** 기준 문서 반영이나 한 번의 비재현만으로 닫은 것이 아닙니다.

1. 원인은 Anvil1.4.4 상태 재기동 때 genesis만 다시 생성되는 문제로 확인됐고, #86이 기존 Reader/Writer의 배포 블록 기준 식별을 보존하도록 수정했습니다.
2. 실제 D 실행은 제품d757a26의 fresh1/mixed3와 제품33396ba의 fresh1/mixed5이며 전 회18개 필수 그룹 통과·자원 정리 true입니다. 다른 체인·같은 ID의 빈 RPC·배포 식별 거부, projection/reorg/재시작, receipt/Operation/checkpoint 회귀를 포함합니다. 이전17 PASS/1 FAIL과 원인 진단 기록은 그대로 둡니다.
3. [B 검토](https://github.com/OriginProof-3web/OriginProof/pull/76#issuecomment-6314138173)와 [C 최종 검토·해결 판정 동의](https://github.com/OriginProof-3web/OriginProof/pull/76#issuecomment-6318989928)를 확인했습니다. C는 두 D 실행과 거부 경계·수정 전 실패를 대조했고 G07에 한정해 판정 동의를 밝혔습니다. 평가 실행기 등 다른 변경의 C 승인으로 확대하지 않습니다.

이 후속 작업에서 live G07을 다시 실행한 것으로 기록하지 않습니다. 새 지갑/Registry/API의 실제 통합·공개 체인·브라우저·단계 완료는 이 해결 범위 밖입니다. 해당 경계에서 새 결함이 나오면 별도 후보·재현 근거로 추적합니다.

## 남은 인계와 사람 확인

- #84의 [A 소비 검토](https://github.com/OriginProof-3web/OriginProof/issues/84#issuecomment-6334429744)·[대표 지시의 대행 검토](https://github.com/OriginProof-3web/OriginProof/issues/84#issuecomment-6334500736)에 이어, 사용자 요청으로 [D 직접 실행 기술 검토](https://github.com/OriginProof-3web/OriginProof/issues/84#issuecomment-6335937751)를 기록했습니다. 결론은 이상 없음이며 아래 실제 검사 근거를 따릅니다. 사람 본인의 대행 커밋 확인·코드 Approve와는 구분합니다.
- C #85 runbook은 이제 seed-only ready503, P0 준비 뒤 ready200, Registry 주소 설정+미주입 때503을 구분합니다. 기존 D의 준비 조건 문서화 요청은 반영됐고, 실제 Registry 주입/새 지갑 왕복 검사는 남습니다.
- B 읽기 Adapter는 병합됐지만 submit/find_transaction은 명시적인 dependency 오류이며 C 생산 주입·중계/Operation 연결, A 실제 왕복은 후속입니다. 실제 API 성능·새 지갑 브라우저/DB/보관·복구 수용과 구분합니다.
- 입력 종류/우선순위·라벨/분할 사람 리뷰·유료 평가 범위/예산이 정해지기 전 실제 모델/보류36개 예측·미선정 변환을 실행하지 않습니다. 모델gpt-6-luna와 Decisions API 범위 밖 결정은 유지합니다.
- 선정 공개 환경(#89는 준비 PR), 다른 노트북·동일 RC3회, phase 승격의 별도 검사/리뷰가 남습니다. 과거 PR을 다시 병합하거나 이번 문서로 기능/단계 완료를 만들지 않았습니다.

## #84 D 소비 검토 기록 — 2026-10-22

첨부된 팀 요청에 따라 Codex가 D 작업 HEAD `fe5aed4d3421fee8f5599190c0f902e6e5f7da87`(phase 기준은 위 f6e7fdb)에서 직접 재검사했습니다. 계약·생성물·기능 코드는 변경하지 않았습니다. 원본 모델의 근거/제한 설명 상한, D 모델 재검증·결합 제한, C ground_report 및 오류 코드를 대조한 결과 **수정 요청 없음**입니다.

| 검사 | PASS | failure/error/skip |
| --- | ---: | --- |
| consumer + 정확 개수 JUnit guard | 31 | 0/0/0 |
| 분석기 phishing 단위 | 68 | 0/0/0 |
| OpenAI SDK MockTransport | 7 | 0/0/0 |
| C 분석 API ASGI/SQLite | 27 | 0/0/0 |
| D 분석 연결 ASGI/SQLite | 12 | 0/0/0 |

뒤 네 행은 별도 실행 합계114개이며 stage43 전체 재실행이 아닙니다. 종전 전체953개와 겹치므로 합산하지 않습니다. consumer31은 보고서 Schema/근거 소비 검사이며 오류 코드·세션 연결 근거는 별도114개와 코드 대조입니다.

- rule_id 1~100자, quote 1~500자·빈 인용 거부, evidence 최대50개, limitations 최대20개·각500자. 원문 일치·Unicode 위치·위치 없는 겹침 인용 거부를 유지합니다.
- LLM 실패 후 규칙 fallback 보고서는 COMPLETED와 `limitations`의 `LLM_ANALYSIS_UNAVAILABLE:<code>`로 표시합니다. 작업 실패는 `AnalysisJob.error_code`에 허용 코드로 기록합니다. 두 경우를 모두 작업 실패로 설명하지 않습니다.
- 선택 verification_session_id의 기존 요청 호환·세션 소유권·C의 발행 검증 부착을 확인했습니다. D가 발행 검증 권한을 주장할 수 없습니다.
- 실제 유료 모델/운영 API·Registry·브라우저 검사는 미실행입니다. 입력 지원은 기본 비활성을 유지했습니다.

재현(저장소 루트, 설치된 `.uv-venv`, macOS는 설치된 Command Line Tools Git PATH):

```sh
export PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH
export PYTHONPATH=services/analyzer/src:apps/api/src:packages/python:services/indexer/src:apps/api/tests
.uv-venv/bin/python -m pytest -q -o addopts= --junitxml=/private/tmp/originproof-d-84-consumer-20261022.xml fixtures/finals/v5_analysis_consumer_qa.py
.uv-venv/bin/python fixtures/finals/v5_d_junit_guard.py /private/tmp/originproof-d-84-consumer-20261022.xml --suite consumer
.uv-venv/bin/python -m pytest -q -o addopts= --junitxml=/private/tmp/originproof-d-84-analyzer-api-20261022.xml services/analyzer/tests/test_phishing.py services/analyzer/tests/test_phishing_sdk.py apps/api/tests/test_wallet_analyses.py fixtures/finals/v5_d_analysis_integration_qa.py
```

이슈 게시 첫 시도는 macOS 기본 Git shim의 Xcode 라이선스 오류로 게시되지 않았고, 설치된 Command Line Tools PATH를 지정한 재시도로 한 번 게시했습니다. 시스템 설정·코드는 바꾸지 않았습니다. JUnit 수치와 해시는 대응 JSON에 기록합니다.

## 다음 D 작업 순서와 필요한 인계

1. **W1/W5 입력·평가 확정:** 팀의 입력 종류/우선순위, A/C의 합성60개 라벨·24/36 분할 리뷰, 유료 호출 범위/예산이 필요합니다. 확정 뒤 기존 제한 평가 실행기로 선정 입력의 실제 gpt-6-luna 평가를 실행합니다. 모델 선택을 다시 요구하지 않습니다.
2. **W2~W5 실제 연결 QA:** C의 생산 Registry/분석기 주입·중계/Operation 복구 인계, B의 submit/find_transaction 지원 범위, A의 실제 v3 웹 경로가 필요합니다. 연결된 후보에서 공동승인·발행·변조·버전·철회·AI/RPC 개별 실패·보관4조합·권한을 재현합니다. C85 readiness 설명 요청은 이미 반영됐습니다.
3. **W6 최종 후보 검증:** 실제 연결 후보 SHA·실행 명령을 받으면 기존 성능/수용/독립 검증 도구로 측정·실패/복구를 확인합니다. 공개 환경·RPC/가스 범위는 B/C/팀 결정 뒤 검사합니다. G07 로컬 legacy 해결을 신규 지갑 전체 완료로 확대하지 않습니다.
4. **W7 재현·리허설:** 동일 RC를 다른 실제 노트북에서 재현하고 전체 흐름3회·영상/대체 장비·제출 링크를 확인합니다. 같은 장비의 임시 Git 검사로 대체하지 않습니다.

지금 가능한 두 기록 작업(G07 범위 판정·#84 D 소비 검토)은 완료했습니다. 이미 구현한 실행기나 통과한 mock 검사를 새 기능으로 중복 개발하지 않으며, 남은 실제 검사에는 위 인계·결정·장비가 필요합니다. PR #91의 작성자 외 리뷰와 사람의 대행 커밋 확인도 별도로 남습니다.
