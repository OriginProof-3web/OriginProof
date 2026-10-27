# D 변환 텍스트 검증·분석·근거 구간 연결

2026-10-23 / 계획5.1·v5-shared-0.2 / V5-W5-D·V5-F14/F15/F16. 사용자 지시로 회의/A·C 리뷰와 독립인 부분을 개발했습니다. 시작 HEAD `5029d345bc06af050bc9e3eee5da35840d315c4f`, branch `codex/v5-d-input-evaluation-review`, phase 기준f6e7fdb입니다. 기존 원본60개·검토 제안·모델/유료 정책·공통 Schema/API·lock과 기여를 보존했습니다. #93/#94는 착수 확인 때 OPEN/미검토이며 이번 작업이 병합을 실행하지 않았습니다.

## 이번 구현과 사용 범위

[converted_inputs.py](../../services/analyzer/src/originproof_analyzer/converted_inputs.py)는 **이미 변환된 텍스트**를 검증해 기존 processor(text)에 전달하고 보고서의 인용을 변환 구간에 연결하는 D 내부 함수입니다. 실제 OCR/STT 구현체·새 SDK·공통 HTTP Schema가 아닙니다. processor를 명시적으로 주입해야 하며 환경 변수에 따라 유료 provider를 자동 구성하지 않습니다. 기본 실제 호출·재시도·키 조회·저장은 없습니다.

1. ConversionSegment/ConvertedText는 extra/타입 강제 변환을 거부하는 private converter output 검증용입니다. 모델 인스턴스/model_construct도 다시 직렬화·검증합니다. text/segments는 repr에 나타내지 않습니다.
2. complete=false·무구간 결과는 INCOMPLETE_OUTPUT로 실패하고 분석기를 호출하지 않습니다. 일부 인식 텍스트만으로 전체 안전/위험 결과를 만들지 않습니다. complete=true는 변환기 선언일 뿐 실제 인식 완전성의 독립 증명이 아닙니다.
3. 공백·줄바꿈·분해 Unicode를 정규화/trim하지 않습니다. 구간 사이의 명시적 newline까지 합쳐 최대10,000 코드 포인트를 검사하고 초과 결과를 잘라서 성공 처리하지 않습니다. 잘못된 Unicode도 processor 전에 거부합니다.
4. DOCUMENT_IMAGE는 단일 이미지의 page1 구간만 허용합니다. AUDIO는 실제 decoder에서 확인한 duration_ms를 caller가 전달해야 하며 300초 이하·시간쌍·범위·순서/비중첩을 검사합니다. 함수가 선언 duration이나 텍스트가 실제 원본 bytes와 일치하는지 독립 검증하지는 않습니다. 겹치는 화자 구간·PDF·다중 페이지 정책은 후속입니다.
5. processor 결과를 기존 validate_analysis_report로 재검증합니다. 발행 검증 권한·없는/모호한 인용을 허용하지 않습니다. 인용이 여러 구간을 가로지르면 각 구간의 실제 교집합을 기록하고 인위적으로 삽입한 separator만의 인용은 거부합니다.
6. report의 AnalysisEvidence는 기존 **변환 텍스트의 코드 포인트 위치**를 유지합니다. 별도 locations는 구간 내 offset·페이지 또는 변환기의 **구간 전체 시간**입니다. 단어별 시간·이미지 bounding box 정확도·실제 파일 검증의 증거가 아닙니다.
7. caller가 전달한 남은 시간(0초 초과·최대180초)에 입력 준비·processor 대기·출력 근거 검사를 포함합니다. timeout/취소·provider 실패 코드를 구분하며 늦게 반환하거나 취소를 삼킨 processor 결과도 deadline 뒤에는 성공으로 반환하지 않습니다. caller/C는 변환 전부터 전체180초와 삭제/late-result fence를 계속 책임집니다.

보고서에 `CONVERSION_ACCURACY_NOT_VERIFIED`, `LOCATIONS_ARE_CONVERTER_SEGMENT_SPANS`를 먼저 예약하고 공유 limitations 최대20개를 지킵니다. 일부 제한 설명을 생략하면 LIMITATIONS_LIMIT_TRUNCATED를 표시합니다. 전체 변환 텍스트·원시 예외/provider 응답을 결과 repr/로그에 담지 않습니다.

## 합성 사용 예 — 실제 OCR 결과 아님

```python
from originproof_analyzer.converted_inputs import analyze_conversion
from originproof_analyzer.phishing import PhishingAnalyzer
from originproof_analyzer.providers import MockLLMProvider

value = {
    "kind": "DOCUMENT_IMAGE", "complete": True,
    "segments": [{"text": "합성 예시: 인증번호를 알려주세요.", "page": 1}],
}
result = await analyze_conversion(
    value, PhishingAnalyzer(MockLLMProvider()), remaining_seconds=180,
)
# result.report: 기존 공통 AnalysisReport / result.locations: private 구간 매핑
```

실제 waveform·이미지는 여기서 전사/OCR하지 않습니다. [PCM WAV 검사](v5_d_media_validation_20261023.md)는 별도 내부 도구이며 decoder 결과를 새 연결에 사용할 때 원본과 메타데이터의 동일성은 변환 어댑터가 책임집니다. 원본/전사 정확도·인식 부족 판정·구간 정답·시간 ±2초 목표는 실제 변환 및 평가 후 확인해야 합니다.

## C/A 인계

현재 C의 text-only ground_report는 page/time을 붙인 보고서를 거부합니다. 이 작업은 그 거부 규칙을 완화하거나 private locations를 기존 응답에 몰래 끼워 넣지 않습니다. C는 실제 업로드/input_ref·원본/변환 텍스트/구간의 관계·타입/오류/보관을 원본 공통 모델에서 조율하고 생성해야 합니다. A는 실제 읽은 범위와 구간 단위 위치·인식 불확실성 안내를 연결해야 합니다. C/A 협의 없이 public contract가 확정/연결됐다고 표시하지 않습니다.

현재 오류 경계는 불완전 변환 INCOMPLETE_OUTPUT, 잘못된 converter object/구간 SCHEMA_MISMATCH, 전체 길이/남은 시간 입력 오류 MALFORMED_INPUT, timeout TIMEOUT입니다. 알려진 AnalyzerError는 보존하고 원시 예외는 PROVIDER_UNAVAILABLE의 안전한 메시지로 바꿉니다. 잘못된 인용/권한은 기존 고정 grounding/authority 오류를 유지합니다. 기존 v1/v2 오류·HTTP 의미는 바꾸지 않았습니다.

## 검증

[신규 검사](../../services/analyzer/tests/test_converted_inputs.py) **39 PASS**: 실제 PhishingAnalyzer+명시적 MockLLMProvider의 규칙 분석과 구간 매핑, Unicode/공백·원문/입력 객체 보존, 시간 범위/중첩·형식 혼합/강제 변환 거부, partial/empty 거부, 총10,000 경계, 조작된 model_construct, deadline/취소/late 응답·출력 검증 중 소진, 인용 누락/구간 경계·trusted limitations와 비노출을 확인했습니다.

분석기 전체+consumer **467 PASS / skip0 / 기존 Starlette 경고1**입니다. 앞선428개에 신규39개가 포함된 범위이며 합산하지 않습니다. Ruff·평가 검토본 --check·문서 링크/원본/생성물/lock 보존·diff PASS. 첫 실행은 surrogate Unicode가 Pydantic에서 먼저 거부돼 예상 오류 코드가 달랐고, converter Schema 단계의 SCHEMA_MISMATCH라는 실제 경계에 맞춰 검사를 수정했습니다. 검증을 약화하거나 입력을 허용하지 않았습니다.

```sh
export PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH
export PYTHONPATH=services/analyzer/src:apps/api/src:packages/python:services/indexer/src:apps/api/tests
.uv-venv/bin/python -m pytest -q -o addopts= services/analyzer/tests/test_converted_inputs.py
.uv-venv/bin/python -m pytest -q -o addopts= services/analyzer/tests fixtures/finals/v5_analysis_consumer_qa.py
.uv-venv/bin/python -m originproof_analyzer.review_packet --check
```

이 결과는 합성 변환 텍스트+규칙/mock 검사입니다. 실제 OCR/STT·음성/이미지 인식 점수·유료 모델·holdout 모델 예측·업로드/DB/브라우저/Registry·단계 수용은 미실행입니다. 회의 후 정할 PDF/세부 코덱·우선순위·호출 범위/상한과 A/C의 평가 검토를 대신하지 않습니다. 공통 보안 #93의 감사 차단은 별도 PR이며 중복 lock 변경/미병합 타인 branch 병합은 하지 않았습니다. G07 로컬 legacy 해결과 #84 기록의 범위도 유지합니다.


2026-10-23 독립 묶음 후속: [외부 취소를 processor가 삼키는 실제 결함을 재현·수정하고 파일형 자료·변환 점수 도구를 추가](../qa/v5-d-independent-batch-20261023.md)했습니다. 위39/467은 당시 실행 범위이며 이번 후속의 새 코드/clean 재현 SHA와 혼합하지 않습니다.
