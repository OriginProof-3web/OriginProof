# D 최종 RC 실행·사용자 이해·리허설 작업표

2026-11-03 · V5-W7-D 준비 · **전부 실행 기록이 아닌 준비 양식**입니다. 계획서5.1의 검사 정의/목표를 바꾸지 않습니다. 기존 검사·수용 실행기·독립 verifier·리허설 안내를 재사용하며 사용자 요청으로 Codex가 양식·근거 연결을 준비했습니다.

- 최종 RC40자리 SHA: **미지정**
- manifest/lock/fingerprint/dataset hash: **미지정**
- 발표 장비·시간·영상/제출 규격: **미정**
- 시나리오 선택: [#117](https://github.com/OriginProof-3web/OriginProof/issues/117), [D AI 기대 초안](../handoffs/v5_d_demo_scenarios_20261103.md)
- 판정: **NOT_RUN_ON_FINAL_RC**. 과거 supporting suite PASS를 accepted=true로 옮기지 않습니다.

## 1. 실행 전 동일성·환경

1. C가 지정한40자리 SHA를 새 checkout에서 확인합니다. 작업 중 HEAD나 phase 최신을 임의로 최종 RC라 부르지 않습니다.
2. lock·추적 schema/ABI/Git tree·manifest chain/Registry·배포/문서 버전을 기록합니다. 기존 fingerprint는 참고하고 Python cache 등 생성/로컬 파일 때문에 달라질 수 있는 값은 추적 소스 hash와 구분합니다.
3. 해당 RC의 실행 runbook으로 전용 합성 DB/Anvil·migration·계정을 준비합니다. 기존 사용자 DB를 reset하지 않습니다. 기본은 mock·추가 유료0입니다.
4. `make generate`, `make lint`, `make typecheck`, `make test`와 해당 RC의 Contract/웹·필요 opt-in 검사를 실행합니다. Python typecheck의 compileall 범위와 실제 취약점 감사 여부를 구분하고 모든 skip 이유를 적습니다.
5. 실모델 시연은 C의 명시적 승인 범위와 실제 사전 확인 기록을 붙입니다. 비밀값·raw provider 응답/원문은 결과표에 넣지 않습니다.

참고 [현재 개인 재현 안내 고정본](https://github.com/OriginProof-3web/OriginProof/blob/4b3f1289b53f2cf88d53f2bac03082c3ec26fbe6/docs/runbooks/w6_rc_personal_reproduction.md). 실제 RC의 UI/명령이 바뀌면 그 버전에 맞춥니다. 현재 Mac의 Node22 실제 사전 실행과 다른 물리 노트북 성공을 혼동하지 않습니다.

## 2. V5-F01~21 실행 기록

각 행에 실제/기대·PASS/FAIL/NOT_RUN·SHA·장비·모델/RPC 방식·증거 URL·실행자를 채웁니다. 아래는 기대 확인 범위이며 결과는 모두 NOT_RUN입니다. 정식 정의는 [계획서14장](../development_plan.md)에 있습니다.

| ID | 확인할 범위 | 실제/증거 |
| --- | --- | --- |
| F01 | 명부/메일/내부 승인/키 보유 누락·자기/타 기관 거부 | NOT_RUN |
| F02 | 1명 거부·서로 다른2명 성공·중복/만료/내용 변경 거부 | NOT_RUN |
| F03 | 단독 정지 뒤 발행 거부·이력·단독 재활성화 거부 | NOT_RUN |
| F04 | 브라우저 원본hash/EIP-712/계약 Golden·중계 변조 | NOT_RUN |
| F05 | chain/contract/action·nonce·deadline·구키 새 발행 거부 | NOT_RUN |
| F06 | 두 기관/템플릿 발행/조회·타 기관 선점/발행/철회 거부 | NOT_RUN |
| F07 | 원본 bytes와 보호 필드 변조 각각 검출·부분/ID 범위 | NOT_RUN |
| F08 | 최신+1·동시 다음 버전 하나 성공·대체/철회 후 과거 상태 | NOT_RUN |
| F09 | 정상 키 교체 과거 발행 보존·유출 경고·정지 중 철회/복구 | NOT_RUN |
| F10 | DB 원본/상태/기관명 조작·삭제 뒤 비교 불가 | NOT_RUN |
| F11 | QR 복사/구버전의 발행 기록·전달 문구/버전 상태 분리 | NOT_RUN |
| F12 | 저장/전송/receipt/DB 사이 중단·UNKNOWN/동일 요청/직접tx/복구 | NOT_RUN |
| F13 | RPC/reorg/재배포/재시작·G07 범위 보존·캐시 성공 금지 | NOT_RUN |
| F14 | 선정 입력 제한/위장/손상·인식 부족·사용자 확인·미지원 | NOT_RUN |
| F15 | 없는 인용 차단·삽입 지시·거절/timeout/fallback 표시 | NOT_RUN |
| F16 | AI높음+공식 정상·AI낮음+불일치·미등록+AI·독립 실패 | NOT_RUN |
| F17 | 보관4조합·타인 접근·삭제/늦은 결과·재시작/기간·기관 원본 독립 | NOT_RUN |
| F18 | 권한/CSRF/제한·비밀 비노출·320px/키보드/대비/오류 읽기 | NOT_RUN |
| F19 | 기존 카드v1·v2 상태/서명·수신자/consume 회귀 | NOT_RUN |
| F20 | API 없이 원본/서명/체인 대조·로컬/공개 달성 구분 | NOT_RUN |
| F21 | 같은 RC/배포/문서·다른 환경·전체 리허설3회·제출 | NOT_RUN |

G07의 과거 해결은 RESOLVED_LOCAL_LEGACY입니다. 이를 신규 Registry 전체 수용이나 영구 무결함 보장으로 확대하지 않고, 과거 OPEN 문구로 다시 미해결 처리하지도 않습니다.

기존 supporting runner는 최종 RC에서 **그 RC의 소스와 정의를 먼저 확인**하고 사용합니다:

```bash
PYTHONPATH=fixtures/finals:apps/api/tests:apps/api/src:packages/python:services/analyzer/src:services/indexer/src \
  uv run --all-packages --all-groups --locked python \
  fixtures/finals/v5_d_acceptance_runner.py --execute --output build/qa/NEW_UNIQUE_RC_RUN
```

현재 알려진 supporting 성공은 최종 수용 BLOCKED를 유지하며 종료코드2입니다. 이를 실패 무시 옵션으로 숨기거나 최종 수용 성공으로 바꾸지 않습니다. 과거112개 지원 검사 기록과 K10 API2개 추가 뒤114개 기대값도 각 버전으로 구분합니다.

## 3. 성능·복구 기록

| 구간 | 실제 기록 칸 | 목표/경계 |
| --- | --- | --- |
| 일반 검증100회 | NOT_RUN /정상수·실패·p50·p95·원문없는config/result hash | p95≤3초 개선 목표. AI/체인 쓰기/브라우저·캐시 효과를 구분 |
| 입력별 AI 지연 | NOT_RUN /모델·변환·분석·실패/보류 | 텍스트p95 10초 초기 목표. 과거 결과를 현재 새 후보로 승계하지 않음 |
| 준비된 장애 복구 | NOT_RUN /주입시점·복구시점·상태·중복tx 여부 | 60초 개선 목표·G07 범위·실제 원인/미달성 별도 |

기존 `fixtures/finals/v5_d_verification_benchmark.py`는 실제 RC 자료로 만든 합성config와 고유 출력 경로를 지정해 재사용합니다. 기대 상태를 측정 응답에서 복사해 정답으로 만들지 않습니다. 오류/잘못된 응답도100개 분모와 지연에 포함하고 두 기관/템플릿을 검사했다면 각각 구분합니다. [사전 로컬 실측](https://github.com/OriginProof-3web/OriginProof/blob/7f1e93793fea0ce6c28ade15a741a7bdb5b1ad54/docs/qa/v5-d-closeout-20261103.md)의 제품 SHA0466633은 최종 RC 판정을 대신하지 않습니다.

## 4. 사용자 이해도5명 실행 양식

계획 목표: **5명 중4명 이상**이 발행 검증/AI 위험/비교 미실행을 구분하는지 확인합니다. 실제 사람을 모집해 같은 RC/화면을 보여 줍니다. AI가 답을 생성하거나 팀원이 대신 채우지 않습니다. 이름/연락처 대신 P01~P05만 기록합니다.

사전에 고정할 질문·채점 기준 초안:

| 질문 | 보여 줄 상태 | 구분해야 할 내용 |
| --- | --- | --- |
| Q1 | 공식 기록/내용 일치·유효 + AI 위험 높음 | 발행 기록 확인과 전달 문구의 위험은 독립이며 한쪽 결과가 다른 쪽을 지우지 않음 |
| Q2 | 미등록 + 뚜렷한 위험 근거 없음/보류 | 미등록은 사기 확정이 아니며 AI 근거 없음/보류도 안전 보장이 아님 |
| Q3 | ID_ONLY 또는 원본 없음/비교 미실행 | ID 기록/상태 조회와 받은 내용의 일치 확인을 구분 |

발행/AI 결합 화면이 실제 준비되지 않았다면 미구현을 성공 화면으로 꾸미지 않습니다. 제품 이해도 검사와 설명용 도식 검사를 구분합니다. 질문을 먼저 검토해 고정하고, 첫 응답3개를 모두 구분한 참여자 수를 기록합니다. 결과를 본 뒤 기준/분모를 바꾸지 않습니다.

| 참여자 | Q1 | Q2 | Q3 | 세 구분 성공 | 화면/RC·익명 메모 |
| --- | --- | --- | --- | --- | --- |
| P01 | NOT_RUN | NOT_RUN | NOT_RUN | 미측정 | — |
| P02 | NOT_RUN | NOT_RUN | NOT_RUN | 미측정 | — |
| P03 | NOT_RUN | NOT_RUN | NOT_RUN | 미측정 | — |
| P04 | NOT_RUN | NOT_RUN | NOT_RUN | 미측정 | — |
| P05 | NOT_RUN | NOT_RUN | NOT_RUN | 미측정 | — |

## 5. 다른 장비·API 밖 검증 인계

다른 실제 노트북 실행자는 RC SHA·OS/CPU·도구/lock/manifest·설치/자동 검사/skip·화면 R1~R5·실패/차이·증거를 기록하고 D가 대조합니다. 같은 Mac 새 clone·CI를 다른 노트북으로 세지 않습니다. 새 장비 구매가 조건은 아니며 팀원 장비의 실제 결과를 사용할 수 있습니다.

API 밖 비교는 기존 `scripts/verify_wallet_document.py`를 원본 bytes·VerificationMaterial·기관 metadata·신뢰할 chain/Registry와 함께 사용합니다. 로컬 Anvil 자료와 기존 Sepolia 자료를 섞지 않습니다. 공개 원본이 없으면 소실/비교 미완료로 남기고 재발행·가스 사용은 별도 결정입니다.

## 6. 같은 RC 전체 리허설3회

최종 시나리오·장비·시간이 결정된 뒤 매 회 전체 동선을 실행합니다. 프로세스 재기동이나 함수3회 호출이 아닙니다. 기능 수정 시 새 RC에 맞춰 검사·리허설 증거를 갱신합니다. [공유 실행 안내 고정본](https://github.com/OriginProof-3web/OriginProof/blob/2a807a30baa72a1ecbaec97d0599790f73bf4260/docs/qa/other-device-reproduction-and-rehearsal.md)을 재사용합니다.

| 회차 | RC/manifest/dataset·장비 | 전체 흐름·소요시간 | AI/RPC 실패 대체·영상/예비 장비 | 파일/링크 접근 | 결과 |
| --- | --- | --- | --- | --- | --- |
| 1 | 미지정 | NOT_RUN | NOT_RUN | 미확인 | NOT_RUN |
| 2 | 미지정 | NOT_RUN | NOT_RUN | 미확인 | NOT_RUN |
| 3 | 미지정 | NOT_RUN | NOT_RUN | 미확인 | NOT_RUN |

## 7. 최종 파일·기여 기록

| 산출물 | 최종 파일/URL·버전·담당·공개 범위 | 열기/권한/내용 대조 |
| --- | --- | --- |
| D01 사용자 웹·D02 기관 웹·D03 운영 웹 | 미지정 | NOT_RUN |
| D04 API/모델/DB·D05 체인/별도 검증 | 미지정 | NOT_RUN |
| D06 AI 평가/한계·D07 실행/수용 패키지 | 미지정 | NOT_RUN |
| D08 발표 원본/제출본·전체/대체 영상·대본 | 미지정 | NOT_RUN |

최종 행사 기한/길이/해상도/자막/제출 채널은 실제 공지를 기록합니다. API/체인·AI/규칙·실측/목표·본인/타인 기여와 사람이 직접 확인한 사실을 구분합니다. 평가 누적133회·정책false와 과거/현재 규칙 버전을 정확히 표시합니다. 발표 자료를 작성했다고 외부 제출·공개/배포 권한이 생기지는 않습니다.
