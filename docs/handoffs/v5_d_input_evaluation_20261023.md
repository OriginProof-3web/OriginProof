# D 입력 선정·A/C 평가 검토 인계 — 2026-10-23

계획5.1 / 공통 계약v5-shared-0.2 / V5-W1-D·V5-W5-D·V5-Q01/Q05. D 사용자 지시로 Codex가 준비했습니다. 최신 phase/W5 `f6e7fdb6727f6b7957d8acc7f3e0bf7e7674ea5f`에서 별도 `codex/v5-d-input-evaluation-review`를 시작했습니다. 기존 #91·사용자 원본·보존 phase·기여 이력을 보존했습니다.

## 이번 사용자 결정

- 입력 종류: **텍스트, 이미지(문서), 음성**. 우선순위는 별도 지정되지 않았습니다.
- 평가는 D가 준비하고 **A와 C가 검토**할 수 있게 공유합니다. 본 문서 작성은 A/C의 검토·승인이 아닙니다.
- 모델은 기존 선택 **gpt-6-luna / OpenAI만 사용**을 유지합니다.
- 예산은 **이번 준비 범위에서 제외**, 호출 범위·횟수도 **미정**입니다. 실제 전송/유료 호출을 허용한 것이 아니므로 기존 opt-in·예산/상한 가드는 유지합니다.
- 이미지(문서)의 PDF 포함·세부 MIME/코덱·처리 우선순위는 미정입니다. 지원하지 않는 형식을 성공으로 반환하거나 PDF/특정 코덱 채택을 가정하지 않습니다.

## A/C가 열어 볼 평가 자료

- [읽기용 60개 검토본](../qa/v5-d-input-evaluation-review-20261023.md): 원문·개발/보류·제안 라벨·인용/코드 포인트 위치·D 판단 근거·경계 flag.
- [구조화 검토 제안본](../../fixtures/synthetic/v5_d_input_evaluation_review_v1.json): A/C의 별도 PENDING 의견칸, source_group/분할을 보존한 세 입력의 파생 계획. 개인 검토 사본 또는 PR 댓글로 실제 의견·reference를 보존합니다.
- 재사용 원본: [합성 원본60개](../../fixtures/synthetic/phishing_sources_v1.json), [기존 D 자체 검토](../../fixtures/synthetic/phishing_sources_v1_review.json). 두 역사 파일과 pinned hash는 변경하지 않았습니다. 그 안의 UNDECIDED는 당시 스냅샷이며 현재 사용자 결정은 위 항목입니다.

원본은 네 위험 수준별15개, 제안 분할은 개발24/보류36(수준별6/9)입니다. 이미지/음성 파생본도 같은 source_group·분할을 유지해야 합니다. 180은 세 형식별 후보 매핑의 수이지 독립 원본 수·필수 제작 수·요구 호출 수가 아닙니다. 실제 평가 범위/호출 수는 미정입니다. 이미지/음성 자산·전사·OCR·영역/시간 정답은 아직 만들거나 평가하지 않았습니다.

### 먼저 판단이 필요한 사례

- 라벨 경계: DP-H05/H07/H08, DP-C11/C14. H08은 인용만으로 문맥이 충분한지도 확인합니다.
- DP-U05/U13/U15는 텍스트 placeholder입니다. 실제 이미지 저품질/음성 인식 실패 평가를 통과한 자료로 세지 않습니다.
- H01/H11/N15, H03/N08/N11, H04/N03/H12/H14의 유사 문구·의미 관계는 기존 자체 검토의 분할 독립성 의문입니다. ID가 다르다는 이유로 독립 원본임을 확정하지 않습니다. 같은 사례의 파생으로 판정되면 D가 원본 그룹/분할 제안을 수정하고 재검사합니다. 검토 전 자동 재라벨링/재분할은 하지 않았습니다.

### 리뷰할 내용과 답변 형식

| 담당 | 검토할 내용 |
| --- | --- |
| A | 원문 문맥에 맞는 위험 표현, 경고/예방 인용과 실제 요구 구분, 인식 부족·미지원 입력 안내, 입력별 필요한 화면/사용자 확인 |
| C | 공유 보고서/인용 계약, Schema·오류/보관 경계, 원문·변환문·위치의 관계, 그룹/분할 누출과 라벨 근거 |

사례별 `ID / 동의 또는 수정 요청 / 제안 라벨·근거 또는 그룹 / 이유`를 PR에 남기거나 JSON 사본에 실제 검토 reference와 의견을 적습니다. 전반 분할에 동의하는지와 입력별 검토 범위도 구분합니다. Codex가 사람 이름·검토 완료·원본 freeze를 대신 기록하지 않습니다. D는 의견을 반영한 새 원본/생성물과 hash·검사를 공유한 뒤 최종 평가셋을 고정합니다. 보류36개는 튜닝 예측에 사용하지 않습니다.

## 입력별 구현·검사 인계

| 입력 | 재사용 | 다음 개발·실제 검사 |
| --- | --- | --- |
| 텍스트 | SemanticInput 1~10000자, 규칙/PhishingAnalyzer·근거 대조·mock/평가기 | C 입력/분석 실제 주입, 선정 범위의 실제 모델 평가 |
| 이미지(문서) | 기존 PNG/JPEG/WebP signature/MIME·5MiB·12MP·1프레임 검증과 카드 vision 경계 | 문서 피싱 분석용 OCR/vision 경로와 변환 텍스트·영역 정답, 위장/손상/저해상도·회전/인용 검사; PDF 포함 여부 별도 |
| 음성 | [PCM WAV 내부 검사 구현·34개 실제 bytes 검사](v5_d_media_validation_20261023.md), 기존20MiB·300초·2채널 기준 | MP3/M4A decoder·STT 구현체, 실제 전사·시간 정답, 잡음/무음/인식 부족·변조 형식·C 업로드 연결 |

위 제한은 기존 계획/이미지 구현을 재사용한 기준이며 새 문서/음성 API가 구현됐다는 뜻이 아닙니다. 현재 C `TextInputRequest`와 D `PhishingAnalyzer(text)`는 텍스트 경계입니다. 이미지/음성 API·receipt·원문 보관·페이지/영역/시간 근거는 C와 단일 원본 계약/생성 경로를 맞춰야 합니다. D는 공유 모델·생성물 또는 C API를 복제/임의 수정하지 않았습니다. 실제 OCR/STT 구현체와 형식이 정해지면 선정 경로의 정상·거부·실패 fixture를 제작합니다.

## 실행과 검증

```sh
export PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH
export PYTHONPATH=services/analyzer/src:apps/api/src:packages/python:services/indexer/src:apps/api/tests
.uv-venv/bin/python -m originproof_analyzer.review_packet --check
.uv-venv/bin/python -m pytest -q -o addopts= services/analyzer/tests/test_review_packet.py services/analyzer/tests/test_phishing_evaluation.py services/analyzer/tests/test_live_evaluation.py
```

검토본 생성기는 기존 load_corpus를 재사용해 원본 hash·60개 ID/중복·라벨·분할·인용을 검증합니다. 읽기용 MD와 JSON을 동일 제안에서 생성하고 기존 파일이 있으면 쓰기를 거부해 사람 의견을 보존합니다. `--check`는 읽기 비교만 수행합니다. 최초 생성은 출력이 없는 경우에만 `--check` 없이 실행합니다.

새 검사7개와 기존 평가/호출 가드27개 **34 PASS**. 분석기 전체+consumer는 **394 PASS / skip0 / 기존 Starlette 경고1**이며 앞34개와 겹쳐 합산하지 않습니다. Ruff·생성물 일치·문서 링크/JSON·diff도 PASS입니다. 네트워크 차단 상태의 export·원본/분할/미검토 상태 보존, 원본 hash/본문 hash/라벨/분할/중복 변조 거부, 생성물 일치와 덮어쓰기 거부를 확인했습니다. 실제 모델 성능 점수·변환 품질·API/브라우저 연결 검사는 미실행입니다. 생성기 최초 실행은 저장소 루트 계산 오류로 실패했고 부모 경로를 수정한 뒤 실제 CLI/자동 생성물 검사를 통과했습니다.

## 후속 담당과 범위

A/C: 이 PR의 사례·분할·입력 계약 의견. C: 이미지/음성 입력·공통 근거 위치/오류/보관 계약 및 생산 주입 인계. D: 리뷰 반영·선정 세부 형식의 변환/실패 자료와 구현·실제 평가 범위 확정 뒤 opt-in 실행. 예산을 지금 답해야 준비를 진행할 수 있다는 요청은 하지 않습니다. 호출 준비가 되면 범위·상한을 별도로 확정합니다. 팀원에게 별도 메시지는 보내지 않았습니다.

G07과 #84 검토는 [별도 완료 기록 PR #91](https://github.com/OriginProof-3web/OriginProof/pull/91)을 따르며 이 입력 준비에서 다시 열거나 신규 전체 수용 완료로 확대하지 않습니다. Decisions API·미선정 세부 형식 활성화·실제 호출·원격 병합은 수행하지 않습니다.


2026-10-23 후속: 사용자 계속 개발 지시로 [D 내부 PCM WAV 검사와 순서별 잔여 작업](v5_d_media_validation_20261023.md)을 구현·검사했습니다. 평가 원본/검토 제안·hash는 변경하지 않았고 실제 전사/유료 호출·A/C 리뷰는 미완료입니다.


2026-10-23 변환 후속: [D 내부 변환 텍스트 검증·근거 구간 연결](v5_d_converted_inputs_20261023.md)을 추가했습니다. 부분 결과를 전체 성공으로 만들지 않고 현재 텍스트 report와 private 구간 위치를 분리합니다. 기존60개 라벨/분할·A/C 미검토 상태는 그대로이며 실제 OCR/STT 품질 평가는 아닙니다.
