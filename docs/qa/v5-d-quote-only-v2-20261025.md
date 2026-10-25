# D 실제 개발 평가 후속 — quote-only v2 오프라인 준비

2026-10-25 / D 여인준 @yijun0330 / Codex 보조 / V5-W5-D 후속·V5-W6-D 준비. 계획5.1·v5-shared-0.2·ADR0003/0004 유지. 사용자가 오류 개선·오프라인 검사·PR 갱신 전부 진행을 지시했습니다. 이번 추가 유료 호출0, 보류36개/이미지/음성0이며 정책false를 유지합니다.

## 실제 관측과 재현 한계

[실제 v1 개발24회](v5-d-live-development-20261025.md)는 source832c218, prompt phishing_analysis_v1입니다. HTTP200 24회·규칙+모델 F1 0.8734·HIGH6/6·근거 거부H01/H05/C01/C02 4건·오분류C02/U04/U06 3건을 그대로 보존합니다. 원시 응답/모델 분류·인용을 저장하지 않았으므로 원래4건의 정확한 필드/숫자를 복원한 재생이라고 주장하지 않습니다. 후보 문구14/14는 원문에 있었으나 원문 자기 위치는4/14, 거부4건은 grounding 검사 단계였습니다. 잘못된 숫자 위치·text에 부적합한 page/time·모호한 반복 등 기존 검증 경계의 문제 유형을 통제된 SDK 응답으로 검사합니다.

## 수정과 재사용

- 기존 공유 AnalysisEvidence를 상속한 provider 전용 _QuoteOnlyEvidence는 source=LLM, start/end offset·page/time을 null로 좁힙니다. 공통 API/Schema/TS/OpenAPI/ABI·C/B/A 구현을 복제/변경하지 않습니다. 모델이 숫자 위치나 text에 page/time을 반환하면 SDK 경계에서 거부합니다.
- 기존 validate_analysis_report가 유일한 exact quote를 Python Unicode 코드 포인트로 찾습니다. 새 위치 보정기/정규화/offset 재시도는 없습니다. 잘못된 명시적 위치·누락·중복/겹침 인용은 계속 거부합니다. 다른 processor의 올바른 명시적 disambiguated span 경로는 유지합니다.
- v1 프롬프트 파일과 실측/ledger는 보존하고 **phishing_analysis_v2**를 새로 추가해 활성 버전을 변경했습니다. 숫자 offset 추정 대신 null·유일한 원문 인용/주변 문맥을 요구하고, 본문 문맥 부족과 단순한 위험 단어 부재를 구분합니다. U04/U06의 생략된 대상을 추측하지 않도록 지침을 보강했습니다. C02는 거부 후 규칙 fallback 결과만 남았으므로 원래 모델의 분류 자체가 틀렸다고 단정하지 않습니다.
- 예시는 평가셋 ID/정답 문장을 복사하지 않은 별도 합성 문장입니다. 기존60개·라벨·기대 인용·분할은 변경하지 않았고 보류36개를 튜닝/평가하지 않았습니다. 특정 문자열/ID를 하드코딩한 위험 규칙을 추가하지 않았습니다.
- 모델 gpt-6-luna·Responses·reasoning low·timeout/retry·저장/도구 정책은 유지합니다. 신규 패키지/환경 기본값 변경0입니다.

[OpenAI Structured Outputs 공식 문서](https://developers.openai.com/api/docs/guides/structured-outputs)는 구조를 제한해도 의미상 오류가 남을 수 있다고 설명하며 지침/예시/작업 단순화를 제시합니다. 이 근거는 v2 실제 성능 검증이 아닙니다. [선택 모델 공식 문서](https://developers.openai.com/api/docs/models/gpt-6-luna)의 기존 모델을 유지합니다.

## 측정 출처를 구분합니다

v2는 raw 모델 offset을 요청하지 않으므로 **기존 v1의 raw 위치 정확도와 비교해 개선/악화를 선언하지 않습니다**. 기존 raw 후보 수/인용·위치 숫자는 그대로 유지하되 provider_offset_mode와 RAW_OFFSETS_NOT_REQUESTED 설명을 추가했습니다. 별도 POST_VALIDATION_LLM_ONLY 지표는 검증 후 LLM 인용·기대 span 포함/정확 일치를 세며 RULE fallback은 제외합니다. 이는 코드가 계산한 위치가 포함된 지표이며 모델이 계산한 위치의 정확도가 아닙니다. 평가 버전0.4, live summary0.2로 구분합니다.

실행기 fingerprint는 활성 프롬프트 파일/hash/version·offset mode를 기록합니다. v1 ledger를 새 v2/다른 코드로 resume하면 HTTP 전에 거부합니다. 완료된 실제24회 기록은 변경/재실행하지 않습니다.

## 오프라인 검사와 미검증

SDK MockTransport·socket 차단으로 다음 경계를 확인합니다. 실제 모델 응답을 흉내 낸 정답을 사용한 검사를 모델 성능 개선으로 세지 않습니다.

- H01/H05/C01/C02의 통제된 잘못된 숫자 범위 거부와 null/정확한 유일 인용→기존 위치 계산·검증 후 LLM span 집계.
- 강제 null wire schema 및 source=LLM; 숫자 offset/page/time·RULE 위조 거부.
- emoji/ZWJ·분해 Unicode·공백/탭/개행의 원문 exact 위치, 정규화/누락/중복/겹침 인용 거부.
- 기존 callback의 올바른 명시적 반복 위치 수용·틀린 위치 거부 유지.
- U04/U06에서 올바른 UNDETERMINED는 유지하나, 의도적으로 잘못된 NO_CLEAR 응답도 구조 검사를 통과하는 **한계**를 재현합니다. 프롬프트 문맥 개선 효과는 실제 재평가 전까지 미검증입니다.
- RULE fallback이 HIGH 정답/기대 위치를 만들더라도 검증 후 LLM 위치 점수에는0으로 남김.
- 활성 프롬프트가 달라지면 ledger resume을 거부하고 새 과금 요청을 보내지 않음.

관련 기존+신규149 PASS 뒤 RULE fallback 분리 검사를1개 더 추가했습니다. 전체 clean 소스 검사·확정 실행 SHA는 다음 결과 JSON으로 연결합니다. 프롬프트/스키마가 API 계정의 실제 새 응답에서도 정상 동작하고 거부/문맥 오류가 줄었는지는 **추가 유료 평가 전 미검증**입니다.

## 다음 단계

이 수정본을 PR94에서 검토 가능하게 공유합니다. 별도의 개발 재평가24회 승인이 도착한 경우에만 새 source/prompt/runtime ledger로 같은 개발 분할을 재평가합니다. 기존24회와 합쳐 총48회가 될 수 있음을 구분하며 승인 전 추가 실행0입니다. 개발 결과 확인 뒤 프롬프트를 고정하고 최종36개1회는 다시 별도 실행 범위를 확인합니다. 현재 토큰 상한 증액·모델 교체·과거 결과 덮어쓰기·라벨/정답 변경·팀 메시지/리뷰 요청·원격 병합·단계 완료는 하지 않습니다.
