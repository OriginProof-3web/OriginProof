# D W6 기준 반영·A/C 평가 확인 — 2026-10-25

D 여인준 @yijun0330 / Codex 보조 / V5-W1-D·W5-D 후속, V5-W6-D 준비. 계획5.1·공유 계약v5-shared-0.2·ADR0003/0004 유지. 사용자가 이전 보고의 작업 전부 시작을 지시했습니다. 단계 완료·사람 코드 승인·원격 병합은 아닙니다.

## 기준과 보존

기존 D head `3c43f5df732c03abebe71c0531ffa9efefdcafa6`에서 clean 상태로 시작해 `origin/phase/W6` = `d0111d82490a0c30d9b36275776487ebd4ba69e8`를 정상 merge했습니다(`3de262f`). #93 보안 패치·#91 G07 문서·#95 W5 승격을 포함합니다. 충돌은 docs/portfolio/W5-D.md 한 곳이며 #91의10월22일 G07/#84 기록을 먼저 두고 기존10월23일 D 기록을 이어 보존했습니다. 공유/보존 branch 직접 개발·force/reset·타인 PR 전체 재병합은 하지 않았습니다. 승인된 lockfile대로 uv sync해 opentelemetry-api1.45.0→1.45.1만 설치했습니다.

## 검토 반영과 자료 정체성

- [C 확인](https://github.com/OriginProof-3web/OriginProof/pull/94#issuecomment-6380482888), [A 확인](https://github.com/OriginProof-3web/OriginProof/pull/94#issuecomment-6381593781), [#92 확정 기록](https://github.com/OriginProof-3web/OriginProof/issues/92#issuecomment-6336600505)을 출처로 메타데이터를 갱신했습니다. 각 댓글의 AI 보조·사용자 지시 설명을 사람의 수동 검사나 코드 Approve로 바꾸지 않습니다.
- 원문60개·id/source_group·라벨·24/36 분할·기대 인용/위치·기존 D basis는 불변입니다. 전체 파일 hash 변경은 버전/확인 상태/입력TEXT/모델·검토 URL/label_status 메타데이터 때문입니다. 기존 hash `944e6e1e…95e9`와 고정 과거 링크를 남겼습니다.
- D 자체 검토의 원래 cases/flags/PENDING 표시는 당시 기록으로 보존하고 현재 corpus metadata에 다시 연결한 hash와 이유를 추가했습니다. 현재 A/C 확인을 D 자체 검토로 대신하지 않습니다. 생성 JSON/MD는 기존 review_packet 생성기로 동기화합니다.
- H01/H11은 같은 요청 문구를 공유하나 A/C 의견대로 분할 유지. 최종 평가를 실행할 때 H11 결과를 별도 표시해야 하며 현재 예측하지 않았습니다. H08의 추가 근거는 선택 권고이므로 검토된 원래 인용을 보존했습니다. U05/U13/U15는 실제 이미지/음성 실패 수로 합산하지 않습니다.
- 문서는 이미지(PNG/JPEG/WebP) 범위이고 PDF 파일은 미선정입니다. 음성 코덱·전사 모델·이미지/음성 실제 평가 승인은 여전히 별도입니다.

## 텍스트 24회 준비·호출 차단

[비활성 개발 정책](../../fixtures/synthetic/v5_d_live_evaluation_policy.development.pending.json)은 #92의 gpt-6-luna/development24회·회당출력1024·총예약24576·원문200자 제한과 새 corpus hash를 담습니다. **approved_for_paid_calls=false**를 유지했습니다. 기존 예시 정책도 false/호출한도0입니다. 최종36개 정책은 프롬프트 고정·개발 결과 확인 전 작성/활성화하지 않았습니다.

현재 실행 환경과 Git 제외 .env에는 키가 없었고 사용자는 키 설정·충전을 확인한 뒤 알려주시겠다고 답했습니다. 자동 승인 검토가 true로 바꾸는 작업을 거부해 해당 변경은 적용하지 않았습니다. 비활성 정책의 plan은 PAID_SCOPE_NOT_APPROVED를 명시하며 실제 API/유료/holdout 예측0입니다. 키·잔액을 추정하거나 실제 호출로 잔액을 시험하지 않았고 결제·충전 설정도 바꾸지 않았습니다. 선불 잔액을 프로그램의 엄격한 금액 hard cap으로 표현하지 않습니다.

재현(네트워크/키/실제 호출 없음):

```sh
export PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH
export PYTHONPATH=services/analyzer/src:apps/api/src:packages/python:services/indexer/src:apps/api/tests
.uv-venv/bin/python -m originproof_analyzer.review_packet --check
.uv-venv/bin/python -m originproof_analyzer.live_evaluation \
  --manifest fixtures/synthetic/phishing_sources_v1.json \
  --policy fixtures/synthetic/v5_d_live_evaluation_policy.development.pending.json \
  --journal build/private/d-development-20261025.json
```

--execute를 붙이지 않습니다. 향후 키/충전 확인 및 정책 활성화 승인이 도착하면 승인된24회만 실행하며 실제 ledger/중단재개·불명 결과 재호출 금지를 유지해야 합니다. 원시 키·provider payload는 Git/로그에 남기지 않습니다.

## 현재 실행과 잔여 범위

관련 단위40 PASS를 확인했습니다. 전체 clean-source 검사/보안 감사/생성물 검사는 새 코드 커밋을 만든 뒤 실행 결과를 별도로 기록합니다. 초기 Ruff 문자열 길이 오류는 줄을 정리해 해결했고 기능 실패로 합산하지 않습니다. 승인 거부를 성공 실행으로 기록하지 않습니다.

C #63·B #96/#97은 아직 미병합입니다. 이번 작업에서 임의로 합치거나 동작을 재구현하지 않았습니다. 실제 신규 서버/브라우저·이미지 OCR/음성 STT·다른 장비·최종 RC 3회는 미실행입니다. G07 RESOLVED_LOCAL_LEGACY와 Decisions API 범위 밖을 유지합니다. PR #94 설명을 현재 기준과 결과로 갱신하며, 팀원 메시지·별도 재리뷰 요청·Approve·원격 병합은 수행하지 않습니다.


## 최종 로컬 검사

실행 소스 `73e2fa07a4c0bc7e842c3d55e55d30f70458d996`의 새 git archive에서 analyzer/core/API import가 새 사본을 가리키는지 확인했습니다. 전체 **1123 PASS /11 opt-in SKIP /0 FAIL·ERROR**, 기존 Starlette 경고1입니다. Ruff·review_packet --check·실제 미디어24/실패 replay12·Makefile의 생성기5개 경로 모두 PASS, 추적 파일 재생성 diff0, 같은 lockfile 보안 감사0건입니다. [환경·hash·JUnit·검토 URL·원본 보존·정책 차단 JSON](../qa/v5-d-w6-baseline-evaluation-20261025.json). 같은 물리 장비/기존 의존성 환경을 사용한 소스 재현이며 다른 노트북/새 OS 검사가 아닙니다.

원본60개 보호 필드와 D 자체 검토 cases를 3c43f5d와 직접 대조해 불변을 확인했습니다. 기존 기준 대비 타 담당 코드·공통 모델/생성물·lockfile 자체 추가 수정0입니다. 실제 신규 DB/EVM/브라우저/유료 모델은 이번 로컬 실행에서 미실행이며, 이후 GitHub의 실제 복구 검사는 CI 결과로 별도 확인합니다.
