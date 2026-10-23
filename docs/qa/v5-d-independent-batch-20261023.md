# D 독립 미디어·평가·실패 재현 묶음 — 2026-10-23

계획5.1 / v5-shared-0.2 / V5-W1-D·W5-D·W6-D 준비 / V5-F14·F15·F16. 사용자께서 팀원 요청을 제외하고 바로 가능한 D 작업 전체 진행을 지시했습니다. 시작 branch `codex/v5-d-input-evaluation-review`, HEAD `c719093b0dc335f3229cd56a0d10a1e5d2b907bc`, phase 기준f6e7fdb입니다. 사람 리뷰·유료/실제 변환 호출·다른 소유자의 API/Schema·공통 lock 변경은 범위 밖입니다.

## 실제 합성 파일·실패 자료

[미디어 manifest](../../fixtures/synthetic/media_safety_v1/manifest.json)와 같은 폴더의 **이미지12개·PCM 파일12개**를 만들었습니다. 총105,716 bytes. 한 합성 문서와 합성 비음성 신호 그룹의 변형24개이며 독립 원본24개/음성 발화/최종60개 평가셋을 뜻하지 않습니다. source_group을 공유하고 development 전용이며 기존60개/24·36 제안·hash는 수정하지 않았습니다.

| 경로 | 실제 파일 범위·기대 |
| --- | --- |
| 이미지 | PNG/JPEG/WebP, blur·low contrast·90도 회전·16x6 저해상도·EXIF orientation, truncation·MIME 위장·multi-frame·signature 위조 |
| PCM WAV | tone·noise·silence·clipped·stereo, truncation·컨테이너 길이·부분 frame·float 위장·빈 파일·extensible PCM 정상/채널 위조 |
| 변환 실패12개 | 텍스트/이미지/음성 각4개. blank/길이/Unicode/type·partial/empty/page/extra·partial/empty/time 누락/범위, 제어된 replay임을 표시 |

저화질·무음·잡음은 **형식 검사에 통과할 수 있습니다**. 해당 통과를 인식 가능·원문 일치·안전 판정·모델 품질로 세지 않습니다. 음성 파일은 사람 녹음이나 합성 발화가 아닌 비음성 신호입니다. 추가 실패12개는 converter/provider 실제 실패의 관측이 아닌 미완료·Schema 거부 경계의 제어 replay입니다. 기존 provider refusal/timeout·취소 검사는 함께 유지했습니다.

[media_fixtures](../../services/analyzer/src/originproof_analyzer/media_fixtures.py)는 decoder/검사기와 명시적 MockLLMProvider만 재사용합니다. 파일 hash/크기·출처/미평가 상태·중복/누락·파일명/path traversal/symlink/미등록 파일을 검사하고 입력 오류12개가 분석에 도달하지 않는지 확인합니다. 생성은 새 경로에만 허용하며 기존 자료를 덮어쓰지 않습니다. 인코더의 플랫폼/버전 차이로 byte가 달라질 수 있으므로 CI는 재인코딩 동일성 대신 **커밋된 byte와 manifest hash·실제 decode**를 검사합니다. generator 환경을 manifest에 기록했습니다.

선명/blur 파일을 직접 열어 합성 안내와 흐림 변형을 확인했습니다. 실제 OCR/STT는 미실행입니다. 자료 모양의 QA와 인식 정확도 검증을 구분합니다.

```sh
export PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH
export PYTHONPATH=services/analyzer/src:apps/api/src:packages/python:services/indexer/src:apps/api/tests
.uv-venv/bin/python -m originproof_analyzer.media_fixtures --output /private/tmp/d-media-new-result.json
# 새 버전만 생성: --generate --root /private/tmp/new-media-version
# 기존 폴더와 기존 output 파일은 덮어쓰지 않습니다.
```

실행 결과는 `OFFLINE_MEDIA_CONTRACT_PASS`, 실제 bytes24/제어 실패12 모두 기대와 일치, invalid conversion의 processor 호출0·유료0·holdout 예측0·semantic evaluation NOT_RUN입니다. 결과에는 ID/숫자/고정 오류·manifest hash만 넣고 원문·provider payload는 출력하지 않습니다.

## 변환 품질 점수 도구 준비

[conversion_metrics](../../services/analyzer/src/originproof_analyzer/conversion_metrics.py)를 추가했습니다. 실제 모델/provider를 부르지 않는 계산기이며 아래 자체 검사는 모델 품질 결과가 아닙니다.

- **문자 오류율 CER:** 공백·분해 Unicode를 보존한 코드 포인트 Levenshtein 거리/정답 문자 수. 삽입이 많으면1을 넘을 수 있고 자르지 않습니다. grapheme/단어 정확도·피싱 확률·보정 confidence가 아닙니다. 빈 분모는null입니다.
- **누락 방지:** 예측 실패(None)와 계산 자원 초과를 별도 집계하고 corpus 전체가 계산되지 않았으면 전체 CER을null로 둡니다. 성공 사례만 평균내지 않습니다. 동일 case ID·잘못된 Unicode/길이를 거부합니다. 쌍당 최대4,000,000 edit cells, 최대10,000 코드 포인트·200 cases를 명시했습니다. 같은 긴 prefix/suffix는 제거해 실제 차이에만 거리 계산을 합니다.
- **시간 위치:** 예상/후보 양 끝점 모두 ±2,000ms 이내여야 일대일 최대 matching으로 셉니다. 중복/무효 후보도 precision 분모에 포함하고 broad span이 정답을 덮는 것만으로 통과하지 않습니다. 기대 annotation 오류·허용 오차 완화는 거부합니다. 변환기 구간 선언에 대한 비교이지 단어별/실제 STT 정확도는 아닙니다.
- **이미지 영역:** 원점 좌상단·pixel `[x0,y0,x1,y1)`의 raw IoU 계산입니다. 명시한12MP 이하 이미지 경계와 정수 좌표를 검사하고 합격 임계값은 임의로 정하지 않습니다. 실제 OCR bbox 입력·최종 공통 좌표 계약·모델 평가 완료를 뜻하지 않습니다.

제어 입력/정답을 써서 insertion/deletion/substitution·Unicode/공백, None/빈 분모/자원 제한, greedy로 놓치는 매칭·중복/잘못된 시간·±2초 경계, disjoint/touch/부분 영역을 검사했습니다. 원문/후보 문자열은 지표 결과에 보관하지 않습니다.

## 실제 재현한 결함과 수정

1. **외부 취소 무시:** injected processor가 CancelledError를 삼키고 정상 report를 반환하면 기존 analyze_conversion이 성공할 수 있었습니다. 새 검사1개가 실패로 재현했습니다. 처리 시작/processor 종료/반환 전에 현재 task의 pending cancellation을 확인해 성공을 차단했습니다. 시작 전 취소도 processor 호출0으로 확인했습니다. 실제 C 삭제/late-result DB fence를 대신하지는 않습니다.
2. **WAVEFORMATEXTENSIBLE 위조4종:** 기존 stdlib reader는 extension size·container보다 큰 valid bits·채널 mask 모순을 거부하지 않았습니다. 새 검사4개가 모두 실패했습니다. fmt chunk의 실제 크기/extension/정밀도/mask 일관성을 추가 검사했습니다. 정상/float subtype·기존 WAV 회귀를 유지했습니다.
3. **허용 경계 회귀:** 이미지 정확12MP·정확5MiB 허용과1byte 초과 거부를 추가 확인했습니다. 기존20MiB/300초 WAV 경계와 함께 보존했습니다.

기술 근거는 [Microsoft WAVEFORMATEXTENSIBLE](https://learn.microsoft.com/en-us/windows/win32/api/mmreg/ns-mmreg-waveformatextensible), [Python task cancellation](https://docs.python.org/3.13/library/asyncio-task.html#asyncio.Task.cancelling)입니다. 처음5 FAIL을 원인/수정 이력으로 남기고 성공으로 덮지 않습니다. 표준 decoder를 제거하거나 기존 제한/오류를 완화하지 않았습니다.

## 검사·재현 상태

- 새 미디어 도구/지표 검사43 PASS, audio/converted 기존+수정78 PASS, 추가 시작 전 취소/이미지 정확 경계2 PASS. 겹치는 범위를 합산하지 않습니다.
- Ruff·신규 파일/manifest·평가 검토본 일관성·원본/hash/공통 계약/호출 가드/lock 보존·문서 링크·diff를 확인합니다.
- 새 실행 코드의 clean 소스 사본 전체 검사와 최종 SHA/환경/정확한 결과는 실행 후 아래에 기록합니다. 동일 실제 노트북·설치 의존성을 재사용한 소스 재현이며 다른 장비/새 OS·실제 DB/RPC/모델 검사를 대신하지 않습니다.

```sh
.uv-venv/bin/python -m pytest -q -o addopts= services/analyzer/tests/test_media_fixtures.py services/analyzer/tests/test_conversion_metrics.py services/analyzer/tests/test_audio_inputs.py services/analyzer/tests/test_converted_inputs.py
.uv-venv/bin/python -m originproof_analyzer.review_packet --check
```

실제 OCR/STT/모델 품질·private source 구간의 원본 정확도·사용자 업로드/API/지갑·공개 환경·다른 실제 노트북·동일RC 리허설은 이번 결과에 포함하지 않습니다. 회의/팀 변경 없이 가능한 도구/안전 검사·재현을 진행했으며 타 담당자에게 메시지/요청·Approve·원격 병합·유료 호출을 수행하지 않았습니다. 기존 보안#93 감사 차단·G07의 로컬 legacy 판정 범위·#84 기록도 변경하지 않습니다.


## 실제 깨끗한 소스 재현 완료

실행 SHA **`be66e6c95f5d62e723c68d1714ac4203959b7990`**를 git archive로 새 임시 폴더에 내보내고 .git 없이 실행했습니다. analyzer/core/API의 import 파일이 모두 그 사본 아래에 있는지 assertion으로 확인했습니다. 설치된 동일 .uv-venv를 재사용했으며 Python3.13.7·Pillow13.0.0·OpenAI2.54.0·같은 lock입니다. 다른 물리 장비나 새 의존성 설치 재현이 아닙니다.

- 전체 기본 Python **1083 PASS / 기존 opt-in11 SKIP / 기존 Starlette 경고1**, 실패/오류0. API/core/indexer/기존 v1/v2·분석기와 신규 검사 포함입니다. skip을 실제 환경 통과로 계산하지 않습니다.
- 실제 미디어 byte24개/제어 실패 replay12개 **기대 일치**, invalid processor 호출0·유료0·semantic evaluation NOT_RUN.
- 검토본 --check와 전체 clean 소스 Ruff **PASS**. 새 source·manifest·원본60개/lock이 작업 branch와 같은 byte인지 hash로 확인했습니다.
- [구조화 결과·실행 환경·해시](v5-d-independent-batch-20261023.json)에 원시 provider/원문 대신 숫자·ID·고정 코드만 보존합니다.

최종 보고 문서 후속 커밋은 위 실행 소스와 구분합니다. 실행 소스 이후 D 코드/테스트·자료가 바뀌면 해당 검증을 갱신합니다. 공통 CI의 의존성 감사 차단은 별도이며 전체 검사 통과가 실제 OCR/STT 품질·A/C 승인·단계 완료를 뜻하지 않습니다.


## SDK 변환 어댑터 후속

팀원 요청 없이 가능한 연결 준비도 계속해 [기본 차단된 이미지 Responses/명시적 모델 PCM 전사 어댑터](../handoffs/v5_d_media_sdk_20261023.md)를 구현했습니다. SDK MockTransport34개가 통과했고 실제 호출·모델/전사 선택·유료 활성화는0입니다. 앞선 be66e6c/1083은 당시 실행으로 보존하고 SDK 후속 소스의 전체 검사는 별도 source SHA로 기록합니다.
