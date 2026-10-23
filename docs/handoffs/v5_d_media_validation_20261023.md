# D 선정 입력 후속 — PCM WAV 검사와 남은 작업

2026-10-23 / 계획5.1 / v5-shared-0.2 / V5-W5-D·V5-F14. 사용자 계속 개발 지시로 Codex가 기존 `codex/v5-d-input-evaluation-review`의 clean HEAD `a51b49facd89cd5094d240d1baa05f866db3baa6`에서 이어서 작업했습니다. 시작 기준 phase/W5는 `f6e7fdb6727f6b7957d8acc7f3e0bf7e7674ea5f`이며 #94 A/C 리뷰·#93 보안 수정은 착수 시 OPEN/미병합입니다. 기존 작업·원본60개·평가 제안·기여 이력을 보존했습니다.

## 이번 구현

[inspect_pcm_wav](../../services/analyzer/src/originproof_analyzer/audio_inputs.py)는 **D 내부 오프라인 검사 함수**입니다. 기존 ADR0003의 PCM WAV·20MiB·300초·최대2채널 기준으로 bytes와 MIME을 받고 PCMInfo 숫자 메타데이터만 반환합니다. 유료 SDK·새 패키지·외부 실행 파일·네트워크를 사용하지 않습니다. 기존 오류 enum과 안전한 메시지를 재사용하고 함수가 파일명·원문·parser 상세를 출력하지 않습니다.

- MIME은 현재 이 검사 함수의 audio/wav·audio/x-wav만 허용합니다. RIFF/WAVE signature·전체 컨테이너 길이·각 chunk 범위를 실제 bytes와 대조합니다.
- 단일 fmt/data 순서·중복·부분 프레임·배포치가 아닌 PCM 정렬/byte rate·표본 폭을 확인하고 Python wave로 PCM 프레임을 읽습니다. 메타데이터 chunk는 범위 안에서만 건너뜁니다.
- 20MiB/300초는 이하 허용입니다. 길이는 frames와 sample rate의 정수 비교로 검사해 반올림으로300초 초과를 숨기지 않습니다. 1~2채널과8/16/24/32bit 정수PCM을 검사합니다. extensible PCM subtype은 표준 decoder가 추가 확인합니다.
- MP3·M4A·다른 MIME/float WAV는 성공으로 대신 반환하지 않습니다. MP3/M4A decoder는 후속이며 PCM WAV를 먼저 구현한 것을 최종 지원 형식/우선순위에 대한 사용자 결정으로 확대하지 않습니다.
- 빈 파일/손상/자원 상한 초과는 기존 MALFORMED_INPUT, 이 함수의 미지원 입력은 UNSUPPORTED_INPUT으로 실패합니다. 기존 v1/v2 AnalyzerError HTTP mapping을 바꾸지 않았습니다.

기술 근거: [Python3.13 공식 wave 문서](https://docs.python.org/3.13/library/wave.html), [기존 ADR0003의 입력/자원 제한](../adr/0003-v4-development-baseline.md). 새 provider/전사 구현체를 선택한 것이 아닙니다.

## 실제 검사·한계

[신규 테스트](../../services/analyzer/tests/test_audio_inputs.py) **34 PASS**. stdlib로 만든 합성 PCM bytes를 실제 parser/reader로 검사했습니다. 이는 mock STT나 실제 사람의 녹음 인식 평가가 아닙니다.

| 범위 | 확인 |
| --- | --- |
| 정상 | mono/stereo·8/16/24/32bit, 홀수 payload, duration_ms 올림, 안전한 metadata chunk |
| 자원 | 정확20MiB 허용/그 이상 거부, 정확300초 허용/한 frame 초과 거부, 채널 초과 |
| 변조/손상 | RIFF 위장·declared size·truncation·부분 frame·비정상 frame 크기·trailing junk·fmt/data 누락/중복·정렬/byte rate/0 sample rate |
| 미지원/안전 | MP3/M4A/video/image MIME 및 잘못된 MIME 타입, float PCM 위장 거부; socket 차단·정적 오류 메시지·원문 비노출 |

분석기 전체+consumer **428 PASS / skip0 / 기존 Starlette 경고1**, 위34개와 기존394개가 포함됩니다. Ruff·평가 검토본 --check·문서 링크/생성물/원본 보존·diff 검사 PASS. 실제 모델/유료 전송/전사/OCR/브라우저·Registry 검사는 실행하지 않았습니다. 테스트 합성 waveform을 발화60개나 holdout 모델 예측으로 세지 않습니다. 최신 CI 결과는 PR #94에서 실행 HEAD별로 기록합니다.

```sh
export PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH
export PYTHONPATH=services/analyzer/src:apps/api/src:packages/python:services/indexer/src:apps/api/tests
.uv-venv/bin/python -m pytest -q -o addopts= services/analyzer/tests/test_audio_inputs.py
.uv-venv/bin/python -m pytest -q -o addopts= services/analyzer/tests fixtures/finals/v5_analysis_consumer_qa.py
.uv-venv/bin/python -m originproof_analyzer.review_packet --check
```

## C/A 연결 인계

이 함수는 이미 메모리에 들어온 bounded bytes를 검사합니다. C 업로드 단계는 별도로 **스트리밍 크기 상한을 적용한 뒤** 호출해야 합니다. 기존 ADR의 413/415/422 HTTP 구분·input_ref/receipt·작업180초/계정 제한·보관/삭제는 C 소유 경계에서 단일 공통 모델로 조율합니다. D가 upload route·별도 Schema·C 오류 mapping을 복제하거나 등록하지 않았습니다.

현재 `SemanticInput`/PhishingAnalyzer(text)는 기존 회귀를 보존하고 음성 bytes를 임의 텍스트로 해석하지 않습니다. STT 후 실제 전사·원문/변환 텍스트/시간 근거, 인식 부족·잡음/무음·낮은 품질 및 일부 인식 표시가 필요합니다. 메타데이터가 정상이라는 이유로 음성이 이해됐다고 표시하지 않습니다. PCMInfo는 서비스 공통 도메인 모델이 아닌 D 내부 decoder 결과입니다.

## D 남은 작업 순서

| 단계 | 지금까지 완료 | 실제 남은 작업·선행 인계 |
| --- | --- | --- |
| W1 | 합성60개·24/36 분할·A/C 검토본/경계 flag | A와 C의 라벨/근거·그룹/분할 검토 반영 후 고정; #94 미검토 |
| W2~W4 | 공동승인/변조/버전/키 상태 합성 QA·기존 독립 로컬 EVM | C 생산 Registry/중계·Operation 연결, A 실제 지갑·웹 인계 뒤 같은 후보에서 기관 격리/공동승인/발행/버전/철회/복구 E2E |
| W5 입력 | 텍스트 분석·이미지 기본 검증, 이번 PCM WAV 실제 bytes 검사 | 문서 OCR/vision 피싱 경로·MP3/M4A decoder·STT·영역/시간 정답·저품질/실패 fixture; PDF 포함·세부 형식/구현체 조율 |
| W5 평가 | 제한 실행기·중단재개·분모/근거 지표·검토본 | A/C 리뷰 반영, 실제 전송/호출 범위·상한 확정 뒤 gpt-6-luna 실제 평가. 예산은 지금 준비 범위에서 제외하므로 유료 실행0 유지 |
| W5 통합 | 합성 위험/발행 독립·보관4조합·late/delete fence QA | C/A 실제 연결에서 AI/RPC 개별 실패·권한/보관/실제 재시작/삭제·근거 표시 검사 |
| W6 | 성능/수용 증거 도구·고정 독립 검증·실제 로컬 CLI | 최종 연결 후보 SHA·실행 인계 뒤 실제 API 성능/실패복구·공개 환경 검증; 다른 실제 장비 재현 |
| W7 | 검사/인계·RC 준비 도구 | 같은 RC 전체 리허설3회, 다른 노트북·영상/대체 장비·제출 링크 확인 |

G07 로컬 legacy 해결과 #84 D 검토는 [PR #91](https://github.com/OriginProof-3web/OriginProof/pull/91)에 기록된 범위를 유지합니다. 이번 입력 개발로 다시 OPEN으로 바꾸거나 신규 실제 수용을 PASS로 만들지 않습니다. #93이 미병합인 동안 phase의 opentelemetry-api1.45.0 보안 감사 실패는 별도 공통 CI 차단입니다. 기존 수정 PR을 중복 구현하거나 미병합 타인 branch를 합치지 않았습니다.

다른 팀원에게 필요한 것은 A/C의 #94 실제 리뷰, C의 업로드/receipt·시간/영역·오류/보관 계약과 생산 주입 인계, B/C의 거래/복구 연결 및 보안 #93 조율, A의 실제 v3 웹 동선입니다. 이번 작업은 팀원에게 별도 메시지를 보내거나 사람 검토/Approve·원격 병합·공개 배포를 실행하지 않았습니다.
