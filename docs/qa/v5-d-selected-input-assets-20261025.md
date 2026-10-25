# D 선정 입력 개발용 자료·최종 텍스트 후보 준비 — 2026-10-25

D 여인준 @yijun0330 / Codex 보조 / V5-W5-D·V5-W6-D 준비. 사용자가 D 작업 전체 진행을 지시하고 v2 개발24회 추가 유료평가를 별도 승인했습니다. 이번 자료 생성기는 provider를 호출하지 않았습니다. 실제 텍스트는 v1/v2 각24·누적48회이며 최종36/이미지/음성0입니다.

## 만든 자료와 제외

[manifest](../../fixtures/synthetic/selected_input_development_v1/manifest.json)는 개발 원본24개만 참조합니다. 한글 문서 PNG23개·녹음 후보 대본22개를 생성했습니다. 원문·라벨·기대 인용·source_group·분할은 보존하며 새 독립 원본23개로 세지 않습니다. 이미지 label은 검토된 텍스트에서 상속했지만 modality 검토/변환 품질은 미검토입니다.

- DP-U05는 A/C 합의의 TEXT_ONLY이므로 이미지/녹음 제작에서 제외했습니다. DP-U13/U15는 보류 분할이며 만들지 않았습니다. 판독 불가라는 문구를 선명하게 그려 실제 OCR 실패로 세지 않습니다.
- DP-U03의 ????는 이미지 글자 정답은 있지만 읽을 발화가 없어 음성 대본에서 제외했습니다. U01의 대괄호 지시문·U02 숫자·C02 URL/영문 발음·전사 표기법은 미정 flag로 남겼습니다.
- [녹음 준비표](../../fixtures/synthetic/selected_input_development_v1/recording_plan.md)는 후보 대본이며 사람이 녹음·검토한 음성 파일0입니다. 별도 로컬 TTS 초안은 아래에 구분합니다. 최종 전사·word/evidence time은 모두null입니다. 텍스트 위치를 음성 시간으로 복사하거나 잡음 fixture를 발화로 대체하지 않습니다.
- 기존 내부 검사 범위인 정수 PCM WAV·20MiB/300초/2채널을 안내하되 STT 모델·MP3/M4A 지원·유료 TTS/STT를 임의 선택하지 않았습니다. 최종 낭독/전사 정답은 녹음과 검토 뒤 작성해야 합니다.

## 렌더링·재현·검증 한계

기존 Pillow로 source text만 한 줄에 그렸습니다. 위험 label/정답/ID/시스템 지침을 이미지에 추가하거나 PNG metadata에 넣지 않았습니다. 설치된 Apple SD Gothic Neo Regular(index0,size28), Pillow BASIC을 사용했고 manifest에 폰트 파일명·sha256·글리프 지원·버전을 기록했습니다. 폰트 파일53MB는 복사/배포하지 않았습니다. CI는 커밋된 PNG23개의 hash/형식/차원·참조와 대본/미평가 상태를 확인하며 macOS 폰트 재렌더링이나 실제 OCR을 실행하지 않습니다. 다른 환경에서 바이트 단위 재생성하려면 같은 폰트/버전이 필요합니다.

Codex가 H01/C02/N03/U03 4개 이미지를 원래 크기로 육안 표본 확인했습니다. 전체23개 사람 검토나 OCR 품질 평가를 대신하지 않습니다. pixel 영역 주석은 아직null이며 원문 코드 포인트 인용만 제공합니다.

```sh
export PYTHONPATH=services/analyzer/src:apps/api/src:packages/python:services/indexer/src
.uv-venv/bin/python -m originproof_analyzer.input_asset_pack
# 생성은 새 빈 경로만 허용하며 기존 asset/사람 의견 덮어쓰기를 거부합니다.
.uv-venv/bin/python -m originproof_analyzer.input_asset_pack --generate \
  --root /private/tmp/new-d-pack --font /System/Library/Fonts/AppleSDGothicNeo.ttc
.uv-venv/bin/python -m originproof_analyzer.review_packet --check
```

asset checker는 source/라벨/전사/시간/검토/과금 결과 위조, 파일 hash·경로/누락/추가·symlink·text-only 배제 위반·폰트 출처 위조·대본 변경을 거부합니다. 기존 review_packet 생성기의 180개는 여전히 후보 매핑 수이며 실제 미디어180개/필수 호출 수가 아닙니다. 현재 개발23이미지/22대본 상태를 연결하고 실행 flag가 export/asset 범위임을 명시했습니다. 실제 텍스트 호출 이력은 [v1](v5-d-live-development-20261025.md)/[v2](v5-d-live-development-v2-20261025.md)에서 확인합니다.

## 최종36개 준비와 남은 일

v2 실제 개발 결과 확인 후 모델 alias/프롬프트·코드/runtime hash를 [텍스트 후보](v5-d-holdout-candidate-20261025.json)에 고정했습니다. 코드 리뷰/RC/최종 모델 승인을 의미하지 않고 모델 공급자의 가중치 snapshot도 캡처하지 않았습니다. 실제36개 전에는 해당 파일 hash/runtime/원본/정책의 일치를 다시 확인해야 합니다. 분석기 소스를 바꾸면 새 후보 검증이 필요합니다.

[최종36개 비활성 정책](../../fixtures/synthetic/v5_d_live_evaluation_policy.holdout.pending.json)은 false·회당1024·총예약36864·원문200자입니다. 현재 preflight는 PAID_SCOPE_NOT_APPROVED이며 실제호출0입니다. 별도로 승인해 실행하면 이전48회와 누적84회가 될 수 있습니다. 추가 충전·모델/포맷·최종 평가 실행을 임의 수행하지 않았습니다.

남은 직접 입력은 음성 낭독 자료와 STT 모델/코덱 선택입니다. C/A 업로드·보관/삭제·서버/브라우저 및 B 실제 배포/Adapter·다른 장비·최종 RC는 통합 인계 뒤 검증합니다. 팀원 메시지·재리뷰 요청·원격 병합·공개 배포는 하지 않았습니다. G07 로컬 legacy 해결·Decisions API 제외·v1/v2 서명/권한/consume 회귀를 유지합니다.


## 로컬 합성 음성13개 추가 (STT·사람 녹음 아님)

[별도 manifest](../../fixtures/synthetic/local_tts_development_preview_v1/manifest.json)에 실제 PCM WAV13개(총2,348,240bytes)를 추가했습니다. URL·숫자·영문·지시문 등 발음/전사 미정 flag가 없는 후보만 사용해 source text/group/split을 유지했습니다. 위험 수준별 표본 수는 균등하지 않아 최종 평가셋이 아닙니다.

설치된 macOS say/Yuna 음성·180wpm·16kHz/mono/16bit를 로컬 fixture 제작에만 사용했습니다. 제품 분석 provider는 OpenAI/gpt-6-luna 그대로이며 Apple 음성을 제품 STT 모델로 선택한 것이 아닙니다. 다운로드·TTS/STT/LLM API·스피커 재생0입니다. 원본 PCM frames는 보존하고 stdlib wave로 header만 canonicalize했습니다. 사람 청취/전사·정답 시간은 검토 전으로 null/false이며 실제 전사 정확도0점/100점 어느 쪽으로도 세지 않습니다.

첫 격리 실행은 say 종료0이었으나4096bytes/0프레임 파일을 만들어 기존 PCM 검사기가 거부했습니다. 일반 로컬 실행은 정상 PCM을 만들었고 모든13개가 실제 비영 프레임/크기·시간·형식 검사를 통과했습니다. 이 환경 차이를 음성 성공으로 덮거나 검사 기준을 완화하지 않았습니다. 실패 probe는 임시 경로의 진단으로 보존하고 Git의 음성13개에는 포함하지 않았습니다.

```sh
# Linux CI도 파일·출처·PCM·미검토 상태만 검사할 수 있습니다.
.uv-venv/bin/python -m originproof_analyzer.input_asset_pack --speech
# 같은 macOS/설치 음성 환경의 새 빈 경로에서만 생성합니다.
.uv-venv/bin/python -m originproof_analyzer.input_asset_pack --speech --generate \
  --voice Yuna --root /private/tmp/new-d-speech-preview
```

음성13개는 미검토 초안입니다. 플랫폼/voice version에 따라 재합성 bytes가 달라질 수 있으며 다른 장비에 같은 음성이 있다고 가정하지 않습니다. native 도구가 없으면 다운로드/다른 유료 서비스로 대체하지 않고 종료합니다. 현재22개 녹음 후보 중 발음 합의가 필요한 나머지와 실제 microphone/잡음 조건은 준비되지 않았습니다. source script를 최종전사 정답으로 복사하지 않고 청취 검토가 필요합니다.


## 최종 검사

코드 **5b9c857e590485ed04be92884e680a37b981455f**의 키/.env 없는 새 git archive에서 전체 **1185 PASS /11 opt-in SKIP /0 FAIL·ERROR**, 기존 경고1을 확인했습니다. 전체 Ruff·검토 생성물·이미지23/대본22/로컬TTS13 checker·공통 생성기5개 모두 PASS, 추적 파일 생성 diff0입니다. [Junit/hash·환경·원본/실측 보존·비활성 정책·한계 JSON](v5-d-ready-batch-20261025.json). 같은 노트북/기존 설치 의존성 재사용이며 다른 실제 장비/음성 청취나 OCR/STT 품질 검사가 아닙니다.

핵심 텍스트 모델 소스와 원문/라벨/분할은 실제v2 실행 이후 바뀌지 않았습니다. 이전 v1/v2 ledger는 모두 불변이고 유료 호출은누적48회, 현재4개 정책은 모두false입니다. 이미지/음성 모델 평가0·최종36개0을 유지합니다. 이후 GitHub CI의 실제 DB/API 복구 검사는 별도 결과로 PR에 기록합니다.
