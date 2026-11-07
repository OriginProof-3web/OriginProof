# D 근거 후보 평가·G07 실행 도구 개발

계획5.1 / v5-shared-0.2, V5-W5-D 평가와 V5-W6-D 재검사 준비입니다. AI(Codex)가 사용자 지시로 D branch에서 구현했습니다. 입력 지원·기관/API/Registry 계약·패키지/lockfile·모델 설정은 변경하지 않았습니다. 기본 provider mock, 모델 선택 gpt-6-luna 유지, 유료 호출0·보류36개 예측0입니다. 실제 모델 품질·G07 해결·단계 완료는 별도입니다.

## 1. 검증 전 후보의 근거 지표

[evidence_evaluation.py](../../services/analyzer/src/originproof_analyzer/evidence_evaluation.py)를 [평가기](../../services/analyzer/src/originproof_analyzer/phishing_evaluation.py)에 연결했습니다. `evaluate_phishing(manifest, provider=...)`의 평가 전용 wrapper가 provider 반환 직후, grounding 검증/위치 추론/규칙 fallback **전** 후보를 집계합니다. 실제 분석기·provider·공유 모델은 바꾸지 않았습니다. provider 요청에는 원문 text만 전달하고 라벨/정답 위치를 넘기지 않습니다. 반환값·로그에는 원시 인용/응답 없이 숫자만 보존합니다.

| 지표 | 정의 |
| --- | --- |
| candidate_quote_count | 거부되거나 Schema가 잘못된 항목도 포함한 전체 후보 수 |
| grounding_ratio | 비어 있지 않은 인용 문자열이 원문에 존재하는 후보 / 전체 후보. 의미 적합성·Schema 성공률과 구분 |
| location_accuracy | LLM 출처·Schema 정상·명시한 시작/끝 코드 포인트가 정확한 후보 / 전체 후보. 누락 offset은 추론해 점수를 높이지 않음 |
| missing_rate | 위치까지 맞는 후보로 포함되지 않은 정답 span / 전체 정답 span. provider 실패 사례도 정답 분모에 남김 |
| annotation_location_recall | 인용 문자열과 경계까지 정확히 맞춘 정답 span / 전체 정답 span |
| duplicate/invalid count | 중복 후보·Schema 불일치를 별도 집계. 중복으로 정답 span 충족 수를 늘리지 않음 |

분모0은 null이며 1.0으로 만들지 않습니다. 넓은 인용의 포함 범위와 정확한 정답 경계를 구분합니다. `COMPLETE/PARTIAL/NOT_EVALUATED`는 **후보 관측 범위**이며 모델 합격/정답률을 뜻하지 않습니다. wire response·provider 내부 Schema 거부는 관측하지 못하며 unreadable/미관측 사례는 따로 표시합니다. 결과 버전은 `v5-d-evaluation-0.3`입니다.

기존 `processor=` 경로는 관측하지 않은 원시 후보를 추측하지 않고 NOT_EVALUATED를 유지합니다. `processor`와 `provider` 동시 지정은 거부해 중복 호출을 막습니다. CLI는 여전히 mock/rules 전용입니다. 실제 OpenAI 평가는 승인된 범위/예산과 라벨·분할 리뷰 후 별도로 수행해야 합니다.

검사: 새17+기존 평가9=26 PASS. 없는 인용·거짓/누락/범위 밖/UTF-16식 위치·반복/겹침·중복·빈 후보·provider 실패·부분 관측·fallback 후 분모 보존·원문/비밀 문자열 비노출을 확인했습니다.

[제어된 합성 replay 결과](v5-d-candidate-scorer-check-20261021.json): 개발24개의 원문 hash에 모두 의도적인 미존재 인용을 반환하도록 설정했습니다. 후보24/일치0/정답span12/누락12, grounding0·location0·missing1입니다. fallback 규칙의 안전한 출력8개와 원시 후보0점이 분리됩니다. scorer 동작 검사이며 실제 모델 품질 점수가 아닙니다. 원본60개·라벨/24·36 분할은 바꾸지 않았습니다.

## 2. G07 후보 사전 검사·반복 실행

[v5_d_g07_runner.py](../../fixtures/finals/v5_d_g07_runner.py)는 기본적으로 사전 검사만 합니다. full commit SHA·현재 origin/phase/W5 포함·#86 수정의 phase 반영·clean QA checkout·후보와 QA의 lockfile 바이트 일치를 확인합니다. 조건이 안 맞으면 exit2/BLOCKED로 Docker·uv 설치·서비스 기동 전에 중단합니다.

명시적인 `--execute`일 때만 잠금 환경에서 기존 [legacy QA](../../fixtures/finals/w5_p0_api_qa.py)에 후보 SHA를 전달해 fresh1회→mixed최소3회를 실행합니다. 각 회 새 UUID 자원을 사용하고, 18개 필수 그룹·제품/QA SHA·mode·lock hash·mock/paid0·정리 완료를 검증합니다. fresh 실패는 중단하고 mixed 실패는 각 회 기록한 채 전체 FAIL로 유지합니다. report/log는 build 아래0700/0600으로 보존합니다. 통과해도 `PASS_REQUIRES_B_C_REVIEW`이며 자동으로 G07을 닫지 않습니다.

legacy runner의 기본 과거9651062 SHA 경로는 유지하고 결과에 LEGACY_FIXED_SHA를 표시합니다. 명시 후보 경로는 MERGED_G07_CANDIDATE로 표시하며 preflight를 다시 검사합니다. 과거 helper는 고정 객체에서 재사용하고 후보에 다른 helper가 있으면 덮어쓰지 않고 실패합니다.

실행은 [G07 절차](v5-d-g07-retest-plan-20261021.md)를 따릅니다. 새27개 단위/안전 검사는 임시 Git 이력과 가짜 child 결과만 사용해 Docker/network 없이 통과했습니다. 실제 mixed QA는0회입니다. 현재 #86은 미병합이고 phase lock과 D QA lock도 #87 반영 전까지 달라 사전 검사 BLOCKED가 정상입니다. 개발 중 dirty 작업트리도 별도 차단됨을 확인했습니다.

## 검사와 기여

코드 기준 `73ef6034a69a0bb1427a4490a65a3de8e6fd8ceb`(평가3fe95d3 + G07 73ef603)과 같은 코드의 working tree를 실행했습니다. 로컬 Python3.13.7/pytest9.1.1/FastAPI0.142.2/OpenAI2.54.0/Pillow13/certifi2026.10.19입니다.

| 실행 | 결과·한계 |
| --- | --- |
| 기존 기본 전체 pytest | 701 PASS / 기존 live opt-in10 SKIP / Starlette 경고1; 실제 연결 전체가 아님 |
| 근거 평가 전용 | 26 PASS (위 전체와 중복) |
| G07 도구 전용 | 27 PASS, 임시 Git·simulated child; 실제 G07 아님 |
| 기존 JUnit guard | 16 PASS |
| D 동일 HEAD stage / consumer | 43 / 31 PASS, 각 skip0; ASGI/SQLite·합성 Registry |
| Python Ruff·diff | PASS |

같은 HEAD CI에 G07 단위 검사를 연결하고 해당 runner/legacy/projection 변경도 trigger로 추가했습니다. 공통 모델·생성물 변경은 없습니다. 기존 테스트·v1/v2·서명/권한/consume·과거 실패/기여 기록을 유지했습니다. 코드 수정/기술 검증은 Codex이며 사람의 직접 확인·외부 승인·G07 종료 판단은 하지 않았습니다.
