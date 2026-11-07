# D 변환 SDK 어댑터 — 기본 차단·실제 호출0

2026-10-23 / V5-W5-D / 계획5.1·v5-shared-0.2. 팀원 요청 없이 가능한 개발을 계속하라는 사용자 지시로 [media_converters.py](../../services/analyzer/src/originproof_analyzer/media_converters.py)를 구현했습니다. 기존 SDK2.54·입력/PCM 검사·ConvertedText·안전한 provider 오류를 재사용하고 새 패키지·공개 API·Schema·기본 provider 설정은 추가/변경하지 않았습니다. 실제 키 조회·클라이언트 생성·실제 데이터 전송·유료 호출은0입니다.

## 실제 SDK 경로 구현

| 함수 | 동작 |
| --- | --- |
| document_image_to_text | 기존 PNG/JPEG/WebP 원본 검사→공식 Responses input_image·Structured Outputs→변환 결과 strict 검증/부분 결과 거부. 설정의 gpt-6-luna 유지, 단일 이미지·high detail·4096 출력 상한·store=false·도구 없음 |
| pcm_to_text | 기존20MiB/300초/2채널 PCM 검증→파일명 input.wav로 고정해 audio/transcriptions의 json 응답→문자열/길이/불완전 결과 검증. 전사 모델은 필수 명시 인자이며 미정/공백/gpt-6-luna는 전송 전 거부. 임의 모델 선택·대체 없음 |

[OpenAI GPT-6 Luna 공식 모델 문서](https://developers.openai.com/api/docs/models/gpt-6-luna)는 텍스트·이미지 입력과 Structured Outputs를 지원하고 audio는 지원하지 않는다고 명시합니다. [이미지 입력 가이드](https://developers.openai.com/api/docs/guides/images-vision?api-mode=responses)의 image data URL과 [파일 전사 가이드](https://developers.openai.com/api/docs/guides/speech-to-text)의 전사 endpoint/json 경로를 현재 설치 SDK의 실제 요청으로 검사했습니다. 이 기능/구조 근거가 계정 접근·실제 모델 품질·API 성공을 의미하지 않습니다. 메인 분석 모델 선택은 바꾸지 않았고 STT 모델은 미정으로 유지합니다.

## 실행 가드·경계

- 기본 enabled=false이며 settings·client를 자동 만들거나 환경 키를 읽지 않습니다. 명시적 enabled=true, openai 설정, caller가 소유하는 AsyncOpenAI client가 모두 있어야 요청할 수 있습니다. **이 조건을 테스트가 fake client로 사용한 것은 실제 유료 승인이 아닙니다.** 앱/CLI/평가 실행기에 자동 연결하지 않았습니다.
- client의 base URL은 https://api.openai.com/v1/ 고정이며 닫힌 client, trust_env proxy·follow_redirects 활성 client는 업로드 전에 거부합니다. 307도 다른 origin으로 재전송하지 않습니다. SDK client._client의 HTTPX 설정 확인은 현재 SDK2.54에서 검사했고 버전 변경 시 테스트를 다시 확인해야 합니다.
- 함수 호출당 HTTP 최대1회, 재시도0입니다. 기존 설정의 호출 timeout과 caller가 준 남은0~180초 제한을 함께 적용합니다. 취소·deadline 뒤 결과를 성공으로 반환하지 않습니다. HTTP client 자원은 주입한 caller가 닫습니다.
- 이미지가 반환한 텍스트는 image kind/page1/no audio time을 검사합니다. partial/unreadable·refusal/incomplete/Schema·timeout/rate limit/provider 장애를 고정 오류로 구분합니다. 실제 OCR 정확도나 완전 인식은 보증하지 않습니다.
- 전사 text는 원본대로 보존하고 단어별 시간은 만들지 않습니다. 현재 위치는 실제 PCM decoder의 전체 clip `[0,duration_ms)`이며 **실제 단어 시간의 근거가 아닙니다**. 이후 analyze_conversion은 CONVERSION_ACCURACY_NOT_VERIFIED/LOCATIONS_ARE_CONVERTER_SEGMENT_SPANS를 유지합니다.
- 오디오 API에는 Responses의 store=false를 지원하는 것으로 가정해 전달하지 않습니다. 실제 전송/보관·호출 범위·상한을 승인한 controller와 사용자 입력/멱등·삭제 경계는 아직 연결하지 않았습니다. 이 어댑터의 bool 인자는 금액 hard cap·승인 기록/중단재개 ledger를 대신하지 않습니다.

## 검사

[실제 SDK MockTransport 검사](../../services/analyzer/tests/test_media_converters.py) **34 PASS**. API key는 synthetic-test-placeholder만 쓰고 socket을 차단했습니다. API/키 조회·실제 이미지 OCR·실제 발화 전사·모델 평가/holdout 예측0입니다.

- 이미지 모델·base64 형식·strict schema·출력/timeout/store/tools·실제 기존 규칙 분석 연결.
- PCM multipart 파일명/bytes·명시적 모델/json·decoder 기반 전체 구간·기존 분석 연결.
- 기본 차단/미정 모델·공식 origin/HTTP 옵션/닫힌 client·잘못된 예산/이미지/PCM의 전송 전 거부.
- refusal/incomplete/partial/잘못된 kind/JSON/전사 문자열·과다 길이·429/503/timeout·취소, 단일 요청/자동 retry 없음·다른 origin redirect 없음·원시 예외 비노출.

```sh
export PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH
export PYTHONPATH=services/analyzer/src:apps/api/src:packages/python:services/indexer/src:apps/api/tests
.uv-venv/bin/python -m pytest -q -o addopts= services/analyzer/tests/test_media_converters.py
```

[앞선 실제 합성 파일·점수 계산기·실패 수정·clean1083 검사](../qa/v5-d-independent-batch-20261023.md)는 해당 be66e6c 실행 기록으로 보존합니다. 이번 SDK 후속의 최종 source SHA/새 clean 전체 검사 결과는 별도 JSON에 기록합니다. 기존60개·24/36·A/C 미검토 상태·모델/유료 정책·shared Schema/API·lock·이전 검증 이력을 덮어쓰지 않습니다. 실제 OCR/STT·유료 범위·서비스 연결·공개 배포/병합/사람 승인·단계 완료를 수행한 것이 아닙니다.


## 최종 clean 소스 검증 · 2026-10-23

실행 소스 `8ab1240dbfeeb96bcf31b62034670a6fac81f788`를 git archive로 새 디렉터리에 내보내 .git 없이 analyzer/core/API import 위치를 확인했습니다. 같은 노트북·설치된 lock 의존성을 사용한 검사이며 다른 PC/새 의존성 설치 재현은 아닙니다. 기본 전체 **1117 PASS /11 opt-in SKIP /0 FAIL·ERROR**, SDK MockTransport **34 PASS** 포함, 전체 Ruff·리뷰 자료 일관성 PASS입니다. 실제 합성 파일24개·실패 replay12개 모두 기대 오류와 일치했습니다. [버전·hash·JUnit·실행 경계 JSON](../qa/v5-d-media-sdk-20261023.json)에 기록했습니다. 실제 OCR/STT/유료 호출·holdout 모델 예측0, STT 모델 미정·기본 비활성·실제 신규 연결 미실행을 유지합니다.

원격 phase/W5 `f6e7fdb6727f6b7957d8acc7f3e0bf7e7674ea5f` 기준을 재확인했습니다. #93은 OPEN이며 기존 opentelemetry-api1.45.0 감사 실패가 c-recovery의 실제 복구 검사 진입을 차단합니다. 소유자 lock 변경을 중복 적용하지 않았습니다. 앞선 be66e6c의1083 검사와 사람/과거 실패 이력은 보존합니다.
