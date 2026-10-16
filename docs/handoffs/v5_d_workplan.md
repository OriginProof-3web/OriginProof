# D 작업 점검·재사용·분석 소비 인계

- 확인일: 2026-10-16, 한국시간. 담당은 사용자님의 **D(AI·합성 자료·평가·독립 QA)**입니다.
- 첫 묶음 브랜치: `codex/v5-w1-d-safety-qa`, 시작 `854ee66274dea388b9c5608bd385d9e8a8d258f2`, 구현/검증 코드 `7e16a70da797311d1d25c50842ad5e7f734f16b5`.
- 기준: [계획서 5.1](../development_plan.md) 8·12·14장, [ADR 0004](../adr/0004-v5-governance-wallet-versioning.md), [재사용 인계](v5_reuse_handoff.md). 본문은 D의 실행 계획이며 공통 계획서를 대체하지 않습니다.
- 원격 fetch 후 integration은 여전히 `33bc4f4`입니다. C #57~#62는 Draft이고 미병합입니다. 제품 기준 계약은 `v5-shared-0.1`을 유지하며 C 후보의 `v5-shared-0.2`는 별도 고정 사본에서 소비 검사했습니다.
- 첫 묶음 당시 상태: **D 첫 구현·독립 검사 묶음 완료 / C 소비 검사 1 FAIL / 실제 연결·소유자 리뷰·단계 완료 대기**. 전체 AI 분석기나 W1~W7 완료가 아닙니다.

## 2026-10-16 후속: 사용자 요청 1·2·3 실행

아래 1~5절은 첫 안전성/소비 검사 묶음의 당시 기록입니다. 후속 결과는 다음과 같습니다.

- **1 분석기**: `codex/v5-w5-d-analysis`에 async 규칙+LLM+원문 대조 구현, 전체 Python 292 PASS. [분석 인계](v5_d_analysis.md).
- **2 평가 준비**: 합성 원본 60개/제안 24·36 분할 초안. 개발 24개 규칙 기준선 macro-F1 0.451863, 보류17. 실제 모델 평가·holdout·라벨 리뷰는 미실행입니다. 입력/모델은 사용자 재확인 결과 미정입니다.
- **3 독립 QA**: `codex/v5-d-independent-qa`에서 C 고정 후보와 D callback의 ASGI/SQLite/합성 Registry 12 PASS, C 환경 Analyzer 251 PASS. 실제 과거 PostgreSQL/Anvil mixed 재검사는 18 보고 그룹 PASS입니다. [현재 QA와 명령](../qa/v5-d-independent-qa.md), [결과 JSON](../qa/v5-d-independent-results.json).
- **미해결**: C 자체 DG12는 그대로이며 D callback에서만 차단합니다. G07은 이번 1회 재현되지 않았지만 원인·제품 수정 근거가 없어 미해결을 유지합니다. 과거 실패를 지우거나 단계 완료로 처리하지 않았습니다.
- **사용자/팀 다음 작업**: Q01 입력·우선순위, Q05 모델·유료 전송/평가 범위 결정, A 또는 C의 60개 초안 라벨/분할 리뷰입니다. B/C의 DG12·G07 수정 인계와 같은 신규 A/B/C 후보의 실제 웹/지갑/Registry 연결은 후속입니다. 원격 push/PR/병합은 수행하지 않았습니다.

## 2026-10-16 추가 독립 작업: 자료 자체 점검·clean 재현·W2~W4

- 합성60개 자체 점검과 사례별 라벨 근거 초안 완료. 경계5개/설명용 표식3개/분할 관계3묶음을 A/C 리뷰 대상으로 남겼으며 원본/라벨/분할은 보존했습니다.
- 실행 SHA `40ab4da11c71d75d26b6b94145e53ee03e3d54a6`의 새 clone·새 venv에서 Python292 PASS, 개발24 규칙 기준선 동일, 생성물 diff 없음·구조/환경/lint/구문 PASS입니다. 같은 장비 재현이며 실제 모델/다른 장비는 미실행입니다.
- 같은 C 고정 후보에 W2 승인12 / W3 내용·DB13 / W4 버전·키5, 합계30 PASS를 추가했습니다. ASGI/SQLite/합성 Registry 경계이며 신규 실제 체인·브라우저·동시성 완료가 아닙니다.
- 최종 공급자 선택은 OpenAI만 사용이며 Jev는 취소됐습니다. 입력·OpenAI 세부 모델/유료 범위·라벨/분할의 A/C 리뷰는 남아 있습니다. DG12/G07은 계속 미해결입니다.
- [실행 보고와 재현 명령](../qa/v5-d-readiness.md), [결과 JSON](../qa/v5-d-readiness-results.json), [사례별 자체 점검](../../fixtures/synthetic/phishing_sources_v1_review.json).

## 1. 기존 작업 확인과 채택

| 기존 자산 | 확인 결과·이번 판단 |
| --- | --- |
| 카드 추출·provider·입력 제한·오류 | 기존 Text/이미지 검증·OpenAI/Mock·SDK 모의 응답·refusal/timeout 등의 검사를 재사용했습니다. 외부 모델 호출 없이 전체 회귀를 실행했습니다. |
| 기존 합성 평가 | Text 8개·메모리 이미지 replay 2개가 10/10 통과합니다. 실제 OCR/모델 성능·새 위험 분류 평가로 합산하지 않습니다. |
| W1-D fixture·v1 회귀·기여 기록 | 기존 구현과 이력을 유지했습니다. R39의 누적 원본과 다른 unsigned v2 사례를 신규 지갑 데이터로 변환하거나 덮어쓰지 않았습니다. |
| R43 `c16de660914389ba8821612aa3d6c64708085185` | D 소유 10개 경로만 고정 원본과 동일하게 선별 재사용했습니다. 후보 확인 헤더·v4 prompt·6개 오추출 fixture·SDK 안전성 검사를 채택했습니다. 과거 PR 전체는 병합하지 않았습니다. |
| R51 `17f78e300b04aa9395fb20f6f76f5313d705db3d` | 기존 브라우저 6 PASS/6 FAIL과 R54/R55의 A 자체 수정 근거를 구분했습니다. 5.0 공동승인·지갑 화면으로 독립 재검사해야 하며 이번에는 재실행하지 않았습니다. |
| R55 / #52의 W5 기록 | 이미 integration에 있는 QA 문서를 유지했습니다. fresh 18 PASS와 mixed 17 PASS/1 FAIL(G07)은 과거 결과이며 이번 통과 수에 합산하지 않습니다. |
| C #57~#62 | 새 누적 기준·기관 확인·발행·버전·분석 보관이 Draft입니다. 다른 담당 브랜치를 병합하지 않고 [#62](https://github.com/OriginProof-3web/OriginProof/pull/62)의 `eaa0d166269833cf7ee49675cfa777b0208c3725`를 `git archive`로 내보내 직접 소비 검사했습니다. |

R43 적용 후에도 카드 HTTP 본문은 기존 공통 모델의 10개 필드이고 v1 판정·서명·Golden은 그대로입니다. 추가 헤더는 미확인 후보와 내용 비교 미수행을 알리는 안내입니다. 서버 확인·grounding을 강제하는 보안 기능이나 신규 피싱 분석 완료로 표현하지 않습니다.

이번에 삭제한 기존 코드는 없습니다. 입력·provider·fixture·검사·기여 이력을 유지할 필요가 있으며, 호출자와 대체 검증 근거 없이 정리하지 않습니다.

## 2. D가 진행할 순서

| 우선순위·작업 | D의 할 일 | 지금 가능한 범위 / 실제 연결 조건 |
| --- | --- | --- |
| 1 · V5-W1-D | 기존 자산·실패 기록 정리, 공유 결과·근거 소비 검사, 입력 후보별 부담 비교 | 이번에 R43 선별 재사용과 30개 근거 replay를 추가했습니다. 팀의 입력 결정 뒤 최종 평가 manifest·라벨·분할을 고정하고 A 또는 C 리뷰가 필요합니다. |
| 2 · V5-W5-D 준비 | 기존 provider를 재사용해 규칙→구조화 LLM→실제 인용 대조→공통 AnalysisReport 연결 | 공통 결과·오류·합성 텍스트 검사는 지금 가능합니다. C의 async `analysis_processor(text)` 경계와 연결하고 모델의 발행 판정은 금지합니다. 실제 입력/모델·유료 전송은 Q01/Q05 결정 후 진행합니다. |
| 3 · V5-W2-D | 자기/타 기관 승인·코드 오류·1명/중복 승인·긴급 정지 거부 검사 | C #59의 합성 API를 소비할 사례는 독립 준비 가능합니다. 실제 E2E는 B Registry/Adapter와 A 화면의 같은 후보 인계 후 실행합니다. R51의 FAIL을 재검사합니다. |
| 4 · V5-W3-D | 두 기관/템플릿·금액/계좌/링크 변조·DB 원문/기관명 조작·QR 복사 | C #60의 계약과 기존 사례를 비교해 준비합니다. 실제 DB/체인/브라우저와 v1/v2 회귀는 같은 통합 SHA에서 검증합니다. |
| 5 · V5-W4-D | 구버전·최신 철회·동시 버전·키 교체/사고·정지/복구 | C #61의 결과 소비와 기존 W4 사례를 재사용합니다. 신규 공개 안내와 기존 binding/consume 회귀를 분리하고 B의 실제 원자성을 확인합니다. |
| 6 · V5-W6-D | 공격·장애·다른 장비/clean 환경·서비스 API 밖 검증, 선정 입력 평가 | G07은 B/C 원인·수정 인계 후 동일 후보로 D 재검사합니다. 과거 FAIL·미실행을 숨기지 않으며 유료 모델 평가는 별도 범위/예산이 필요합니다. |
| 7 · V5-W7-D | 동일 RC의 리허설 3회·대체 장비/영상·제출 파일 확인 | A/B/C 통합 인계와 실제 수용 결과가 선행합니다. 미래 통과·일정을 미리 기록하지 않습니다. |

사용자님이 팀 회의에서 확정할 D 관련 항목은 **Q01 입력 종류·우선순위·제한**, **Q05 최종 모델·변환 구현체·유료 평가/전송 범위**, 라벨/평가셋의 A 또는 C 사전 리뷰입니다. 이는 공통 결과·오류 검사를 멈출 이유가 아닙니다.

추가할 것은 실제 근거 대조·모호한 인용·부정문/공식 경고/인용된 사기 예시·prompt injection·AI/발행 결과 조합 검사입니다. 자동 필수화하지 않을 것은 모든 OCR/STT/PDF 경로·180입력 평가·Decisions API·무승인 유료 실험입니다. 기존 이미지 코드는 보존하되 최종 입력 선정·실제 Vision 성공으로 해석하지 않습니다.

## 3. 이번 구현과 검사

새 [30개 합성 replay](../../fixtures/synthetic/analysis_consumer_cases_v1.json)는 실제 위험 분류 평가용 60개 원본과 별개입니다. 원문·모델 출력을 고정 주입해 인용/위치·Schema·모델 권한을 검사합니다. fixture의 `NOT_RUN`은 정의 상태로 보존하고 [별도 실제 결과](../qa/v5-d-consumer-results.json)에 실행 상태를 기록했습니다.

| 검사 | 실제 결과·범위 |
| --- | --- |
| D 현재 브랜치 전체 Python | **213 PASS / 0 FAIL / 0 SKIP**, 기존 Starlette/anyio deprecation warning 1. API 단위/ASGI·mock·코어·Analyzer·fixture 회귀입니다. |
| D Analyzer를 C 후보의 모델·lock 환경에서 실행 | **172 PASS / 0 FAIL / 0 SKIP**, 기존 Starlette TestClient deprecation warning 1. D 변경의 소비 호환성 검사이며 실제 C API E2E가 아닙니다. 전체 213개 검사와 겹치므로 합산하지 않습니다. |
| C #62 직접 근거 소비 QA | **30 PASS / 1 FAIL / 0 SKIP**: 30개 replay와 계약 버전 검사 1개. Unicode·NFD·공백·반복 위치·허위 인용·page/time·Schema 제한·발행 판정 위조를 검사했습니다. |
| 기존 합성 추출 평가 | **10/10 PASS**, prompt v4, Mock image replay. 미확인 후보·내용 비교 미수행이 평가 출력에 명시됩니다. |
| Ruff·compileall·diff | PASS. Python compileall은 정적 타입 검사와 구분합니다. |
| `make generate` | 재생성 후 공유 Schema/TS/OpenAPI·ABI·Golden·예시 diff 없음. 공통 모델·생성 경로·lockfile은 수정하지 않았습니다. |

D 환경은 Python 3.13.7 / pytest 8.4.2 / 기존 고정 lock입니다. C 소비 환경은 별도 고정 사본의 Python 3.13.7 / pytest 9.1.1 / FastAPI 0.142.2 / Starlette 1.7.0입니다. 두 환경을 혼합 설치하지 않았습니다. C 후보의 오프라인 캐시에 없던 고정 패키지만 원래 배포처에서 받았으며 새 의존성을 추가하지 않았습니다. 검사 중 모델 유료 호출은 없습니다.

## 4. C 인계 — 겹친 반복 인용의 모호성

- 대상: #62 `eaa0d166269833cf7ee49675cfa777b0208c3725`, `apps/api/src/originproof_api/wallet_analyses.py`의 `ground_report`.
- 실패: `DG12-overlapping-ambiguous-quote`.
- 원문 `하하하`, quote `하하`, offset 생략. 실제 가능한 범위는 **[0,2), [1,3)** 두 곳입니다.
- 기대: 위치가 모호하므로 `GROUNDING_MISMATCH`.
- 실제: 통과하면서 첫 범위 [0,2)를 채웠습니다. `str.count`가 겹친 등장 위치를 세지 않아 1로 반환하기 때문입니다.
- C 수정 제안: 첫 `find` 뒤 **첫 위치+1부터 두 번째 등장 여부**를 확인해 겹친 반복도 거부합니다. 명시된 유효 offset은 계속 허용해야 합니다.
- 상태: **미해결, C 소유 코드 수정·동일 QA 재검사 대기**. 실패를 xfail·skip·PASS로 바꾸지 않았습니다. C 소스를 직접 수정하지 않았으며 이 문제는 G07과 별개입니다.

C 후보의 소비 검사는 일반 pytest 경로 밖의 [D QA 모듈](../../fixtures/finals/v5_analysis_consumer_qa.py)을 명시 실행합니다. 네트워크 연결은 검사 fixture가 차단합니다.

```sh
# 저장소 루트: 원격 객체를 이미 fetch한 상태에서 실행합니다.
OP_D_ROOT=$(pwd)
OP_C_QA=$(mktemp -d)
git archive eaa0d166269833cf7ee49675cfa777b0208c3725 | tar -x -C "$OP_C_QA"
cd "$OP_C_QA"
UV_PROJECT_ENVIRONMENT=.uv-venv uv sync --frozen --all-packages --all-groups
PYTHONPATH="$OP_C_QA/apps/api/src:$OP_C_QA/packages/python" \
  "$OP_C_QA/.uv-venv/bin/python" -m pytest -q -o addopts= -p no:cacheprovider \
  "$OP_D_ROOT/fixtures/finals/v5_analysis_consumer_qa.py"
# 이 고정 후보의 실제 종료값은 1: 30 PASS / DG12 1 FAIL.
```

## 5. 남은 경계와 공유

실제 PostgreSQL·새 Registry/RPC·지갑·브라우저 E2E·G07 혼합 환경·실제 모델/정량 성능·공개 배포는 이번에 실행하지 않았습니다. C #62의 근거 함수 직접 검사를 실제 HTTP/보관 4조합 성공으로 확대하지 않습니다. C의 자체 검사 결과를 D 독립 승인으로 대신하지 않습니다.

D 전체 소비 리뷰와 A/B/C 소유자 리뷰·사람의 기여 확인은 아직 없습니다. R43의 D 코드 채택은 로컬 완료지만 확인/정정 UI·서버 강제 연결은 후속이므로 전역 재사용 항목을 완료로 옮기지 않습니다. 원격 push·PR 생성·병합과 팀원 메시지 전송은 하지 않았습니다.

Codex가 기존 자산 비교·선별 재사용·검사·인계 초안을 수행했습니다. 사용자님은 D 역할과 착수를 지시했으며 사람의 코드 리뷰·라벨 합의·완료 승인을 에이전트가 대신 기록하지 않습니다. 상세 개인 작업은 [W1-D 기록](../portfolio/W1-D.md)에 연결합니다.
