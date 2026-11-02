# W6 A — 멘토 기준 web-v5 시연 화면 보완 (부분 완료)

## 기본 정보

- 역할·담당: A 김형준님 `@kimhyounjun`; 이번 수정·실행·기록은 Codex 에이전트 키티 프라이드(개발)가 수행했습니다. Git 작성자나 사람의 검토를 대신 주장하지 않습니다.
- 실제 작업 기간: 2026-11-02 ~ 2026-11-02 (이 미커밋 보완·감사 재작업 기준, W6는 달력 주차가 아님). 기존 커밋 이력은 아래 별도 기록합니다.
- 단계·작업 ID: V5-W6-A, V5-F18 접근성·대비 및 멘토의 기술 증명 요구.
- branch: `feat/a-member-ai-keys`.
- 시작·검증 기준 SHA: `31d61afc363b083eef325d5dc4ab08f994d7bf0f` + 이번 미커밋 변경. 최종 커밋 SHA·단계 완료 PR: 미생성(사용자 금지).
- 이번 감사 재작업 시작 시 `git status --short`: business.html, adapter.js, api_adapter.js, chain_check.js, op5_connect.js, text_tools.js, op5_mentor_remaining.test.js 수정 및 op5_w6_demo.test.js, 이 기록 미추적. 기존 변경을 보존했습니다. `.git` 쓰기 금지로 fetch 미실행, 원격 최신 상태 미확인.
- 최신 감사 재작업 수정 범위: `apps/web-v5/페이지/js/adapter.js`, `apps/web-v5/시험/op5_w6_demo.test.js`, 이 기록만. 아래 기존 구현 기록은 이전 미커밋 작업을 포함합니다. API·모델·계약은 읽기 조사만 수행했습니다.

## 목표와 실제 결과

상단 한 줄 결론·다음 행동, 기록 없음은 가짜라는 뜻이 아니라는 안내, 결과의 원문 JSON 제외를 유지했습니다. 계정·테마 단추를 대화 스크롤 밖 상단 줄로 옮기고 밝은 테마의 경계·기술 증명 색과 긴 제목 배치를 보완했습니다. 키보드 기본 요소와 DOM 순서, Sepolia 거래 링크의 정상·거부 조건을 코드와 가짜 DOM으로 검사했습니다. 로컬 시험은 실제 화면·Tab·실서버 연결 성공을 의미하지 않습니다. 본부 제공 브라우저 실측은 아래에 별도 인용합니다.

2-of-3 승인 기록은 기존 API만으로 일반 결과와 연결할 수 없어 `제공되지 않음`을 유지했습니다. 따라서 본선 전체·W6 단계 완료가 아닌 독립 UI 구현·검사 완료 및 연결 대기입니다.

## 개인 기여와 협업

| 작업 ID | 수행한 일 | 재사용·다른 담당자 기여 | 근거 PR·커밋·리뷰 | 상태 |
| --- | --- | --- | --- | --- |
| V5-W6-A / 기존 이력 | 회원 AI 키·멘토 결과 정리, 미등록 안내 회귀를 현재 기준으로 확인 | 기존 A 페이지·API adapter·시험을 재사용 | git log의 `1ccbc3f`(2026-10-31 W6 서버 연결), `233b43b`(2026-11-01 멘토 결과·회원 키), `38c0b3a`(2026-11-02 미등록 회귀); 커밋 제목과 소스 존재 확인, 이번에 구현한 것으로 합산하지 않음 | 기존 근거 |
| V5-W6-A / 이번 작업 | 상단 줄 분리, 밝은 경계·증명 색, 기본 키보드 접근 검사, 조건부 거래 링크, 43개 회귀(지정 전체 명령에 포함), 기여 기록 | 기존 `explorerLinks`, native details/summary/button/textarea, 가짜 DOM 하네스 재사용 | 이번 미커밋 diff와 `op5_w6_demo.test.js`; PR 없음 | 독립 검사 완료 |
| V5-W6-A / 승인 연결 | C API의 권한·모델·식별자 조사 및 요청 초안 작성 | C의 governance API·Python 모델, B의 wallet Registry RPC 경계는 원저자 구현 | 아래 API 조사 근거; 소유자 소비 리뷰 미수행 | 실제 연결 대기 |

## 주요 결정과 문제 해결

- 겹침 원인: 로그인·테마가 main 기준 absolute여서 대화 스크롤 위에 남았습니다. padding만 대화 시작에 더하면 스크롤 후 다시 겹치므로, 스크롤 밖 `chat-tools`에 60px 높이를 확보했습니다. 1100px 이하 및 패널 접힘에는 펼치기 단추 공간 58px을 확보했습니다. 단추 모양·동작은 재사용했습니다.
- 밝은 모드: 기존 light 경계색 `#cfd2d8`은 흰 칸과 구분이 약했습니다. `--c-line-strong:#858b96`과 초점색을 사용하고 기존 전역 muted/line 변수도 밝은 값으로 맞췄습니다. 결과·기관 승인 구역 글자, 기술 증명 링크·pre, 입력 placeholder에 테마 색을 명시했습니다. 긴 summary는 고정 34px 대신 최소 높이로 처리했습니다.
- 감사 대비 보완: 밝은 --z-ai를 #99530b, --t-ok를 #176b42로 낮췄습니다. z-ai/z-ai-bg, 모든 t-* 칩 및 c-faint와 z-fact-bg·z-ai-bg·c-panel의 대비를 4.5 이상으로 검사합니다. 입력창·보내기의 tabindex는 실제 business.html 시작 태그를 읽어 검사합니다. 가짜 DOM은 해당 속성을 복사하지 않으므로 직접 DOM 검사라는 이전 설명을 정정합니다. 입력창·보내기 각각에 tabindex="-1"을 삽입한 메모리 사본 2개가 모두 검사에서 거부되었습니다.
- 키보드: summary·시연 button·textarea·submit button은 기본 키보드 요소이며 음수 tabindex가 없습니다. 시연 → 입력 → 보내기는 실제 HTML 순서, 기술 증명은 앞선 대화에 생성됨을 검사했습니다. 빈 입력의 보내기 disabled는 유지하고 입력 후 활성화를 확인했습니다. 실제 Tab 이벤트·브라우저 접근성 트리는 검사하지 않았습니다.
- 거래 링크: 본부의 최신 결정에 따라 Sepolia의 유효한 20바이트 레지스트리 주소는 hash 유무와 관계없이 링크를 유지하고, 거래 링크는 유효한 32바이트 hash에만 표시합니다. 다른 체인에서는 링크가 없습니다. 잘못된 주소·hash는 해당 링크만 만들지 않습니다. 기존 explorerLinks에서 공통 검증하며 op5_connect.js의 체인 결과 링크 추가 경로(기존 230행)를 유지하고 기술 증명 안의 href 중복만 차단했습니다. op5_mentor_remaining.test.js 기대값도 주소 링크 유지로 정정했습니다. 실제 Sepolia 거래 연결은 미실행입니다.
- foldNarrow: op5_auth.js의 기존 함수와 start의 호출을 보존했습니다. 실제 함수 소스를 실행해 320·375·759·760px에서는 번들 접기 단추가 나타난 뒤 한 번 클릭되고 761·1280px에서는 클릭되지 않음을 검사했습니다. business.html의 스크립트 로드도 검사합니다. 사용자가 좁은 화면에서 메뉴를 직접 펼친 경우는 이번 범위에서 제외합니다.
- 예시 자료: 저장소에 sample_data.js의 생성 원본·생성기가 없어 생성 파일을 손으로 수정하지 않았습니다. adapter의 화면용 복사본에서 assumption·출처·메모와 내부 경로·시안 설명을 정리하고 모든 예시 결과를 렌더링해 미노출을 검사했습니다. 동일 예시 객체를 반환하는 기존 계약도 보존했습니다. 가져온 생성 파일에는 내부 원자료가 남지만 사용자 화면과 복사 결과에는 노출되지 않습니다.
- 발행 서명: 기존 GET /v3/documents/{document_id}/verification-material?version={version}을 결과 렌더링 뒤 비차단 조회합니다. 응답의 문서 ID·버전과 65바이트 서명 형식을 확인한 뒤 signature 행만 보완하며, 기관 발행 서명으로 표시합니다. 2-of-3 승인 기록이나 판정을 바꾸지 않습니다. 정상·403 권한 거부·410 보관 만료·500·네트워크 거부·응답 대기·버전 불일치를 검사했습니다. 실패·대기에는 signature: 제공되지 않음을 유지합니다. 기관 담당자 메뉴의 접힌 원문 JSON은 보존했습니다.
- 최초 전체 시험은 387개 중 1개 실패(예시 객체 참조 동일성 회귀)였습니다. 화면용 복사본을 재사용하도록 수정한 뒤 동일 명령의 최종 시험은 모두 통과했습니다.
- 작성자 외 리뷰: 미실행. 멘토 기준은 사용자 제공 지시를 적용했으며 별도 멘토 확인을 받지 않았습니다. [ADR 0004](../adr/0004-v5-governance-wallet-versioning.md)의 공동승인과 발행 서명 구분을 유지했습니다.

## 승인 기록 API 조사와 C 요청 초안

확인한 현재 코드:

- `apps/api/src/originproof_api/wallet_governance.py`: `GET /v3/proposals/{proposal_id}` → ProposalView. `proposal_view`가 RPC의 proposal과 저장 내용을 대조합니다. `wallet_runtime.py`의 operator는 세션의 operator 역할, 등록된 운영자 주소 및 실제 is_approver를 요구합니다. 일반 회원에게 사용할 공개 API가 아닙니다.
- `packages/python/originproof_core/wallet_contract.py`: ProposalView는 proposal_id, proposal(기관/action/key 등), status, approvals 주소 목록, threshold=2, operation_id를 제공합니다. VerificationResult와 DocumentView에는 승인 proposal_id 연결이 없고 VerificationMaterial은 signing_request/signature/block 위치만 제공합니다.
- `wallet_onboarding.py`: `GET /v3/issuer-applications/{application_id}`는 해당 기관 권한이며 internal-approvals는 내부 확인 단계입니다. 온체인 2-of-3 증거로 바꿔 표시할 수 없습니다.
- `chain_management.py`: `GET /v1/issuer/status`, `/v1/issuer/keys`는 자기 기관 역할 조회이고 v3 문서의 승인 proposal 연결·승인 이벤트 증거를 제공하지 않습니다. 지갑 Registry의 issuer/key/proposal RPC는 서버 내부 경계이며 결과 화면이 권한을 우회해 호출하지 않습니다.

C에게 요청할 **미확정 초안**: `GET /v3/documents/{document_id}/governance-evidence?version={version}`. 현재 검증 결과의 document_id/version/issuer_id/key_id와 정확히 연결된 증거만 반환해 주십시오. 기존 문서 공개·제한 조회 권한을 서버에서 동일 적용하고 일반 회원에게 운영자 권한을 요구하거나 부여하지 않는 읽기 전용 경로가 필요합니다.

문서 발행 거래 식별값도 필요합니다. 해당 document_id·version의 publish tx_hash(성공 receipt·문서 이벤트와 대조된 값), 또는 이를 찾을 공개 읽기 경로를 제공해 주십시오. 공개 문서는 일반 조회 권한, 제한 문서는 기존 수신자·기관 소유권을 서버에서 적용해야 합니다. 운영자 권한 우회는 하지 않습니다. 이 값·읽기 권한이 없으면 실서버에서 Etherscan 발행 거래를 시연할 수 없습니다.

제안 응답 필드: document_id, version, issuer_id, key_id, chain_id, verifying_contract, checked_at, evidence_status(AVAILABLE/UNAVAILABLE/UNKNOWN), proposals 배열. 각 proposal에는 proposal_id, action(활성화/키 교체/재활성화 구분), status, threshold, approvals(approver 주소·tx_hash·block_number·block_hash·log_index), execution_tx_hash 및 확인된 실행 위치가 필요합니다. 문서 발행 서명 자체가 공동승인이라는 뜻으로 표시하지 않습니다. 누락은 null/빈 배열과 사유를 반환하고, DB 승인 수나 tx hash만으로 실행 성공을 선언하지 않아야 합니다. 이 초안은 C/B 검토 전이며 원본 모델·생성 타입 변경은 수행하지 않았습니다. 기존 API의 권한 완화도 요청하지 않습니다.

## 검증·시연 증거

| 사례·명령 | 기대 결과 | 실제 결과 | SHA·환경·데이터 | 증거 |
| --- | --- | --- | --- | --- |
| `op5_w6_demo.test.js` (아래 전체 명령으로 실행) | 정상·거부 43개 통과 | 최신 재작업 단독 실행 43 pass / 0 fail / 0 skip, 종료 0, duration_ms 5023.133917; 최초 단독 실행에서는 서명 정상 응답 모사의 text() 누락으로 1개 실패 후 모사 수정 | 시작 SHA + 미커밋, macOS, Node v26.0.0, 합성 응답·가짜 DOM | [시험](../../apps/web-v5/시험/op5_w6_demo.test.js) |
| 아래 지정 전체 명령 | 기존 결론·안내·증명 및 신규 검사 회귀 없음 | 최종 388 tests / 383 pass / 0 fail / 5 skipped / 0 cancelled / 0 todo, 종료 0, duration_ms 9624.289083 | 같은 기준 SHA + 최종 미커밋, Node v26.0.0 | 저장소 시험 재실행 가능; 브라우저/실제 API 아님 |
| `git diff --check` | 공백 오류 없음 | 통과 | 최종 작업 트리 | diff |
| 320px·375px·1280px 화면 / 실제 Tab / 실제 API·Sepolia | 겹침·넘침·동선·실거래 확인 | 본부 실측은 아래 인용. 에이전트 브라우저 실행 및 실제 API·Sepolia는 미실행 | 본부의 수정 전 트리 실측 | 제공된 결과이며 이번에 재실행하지 않음 |

지정 전체 명령:

```sh
node --test apps/web-v5/시험/*.test.js apps/web-v5/시험/*.test.mjs apps/web-v5/시험/가져온/*.test.js apps/web-v5/시험/가져온/regression/*.test.js
```

5개 skip은 기존 시험의 의도적인 제외이며 이번에 추가하지 않았습니다. 최종 실행 결과 수치는 지정 전체 명령의 실제 출력입니다. 성능·개선율은 측정하지 않았습니다. 브라우저·화면 캡처·PDF·설치·유료 호출·외부 전송·커밋·push·PR·병합은 수행하지 않았습니다.

## AI 활용과 본인의 판단

- 도구·범위: Codex가 기존 지침·소스·git log 조사, API 연결 가능성 검토, HTML/CSS/JS 수정, Node 시험 작성·실행, diff 검토, 이 기록 초안을 수행했습니다. AI 활용 비율을 추정하지 않습니다.
- 사람의 판단: 사용자가 허용 경로·금지 행위·멘토 화면 기준과 실행 명령을 지정했습니다. 김형준님의 이번 코드 직접 수정·최종 검수·승인을 에이전트가 대신 확인하지 않았습니다.
- 재사용과 판단: native 키보드 동작과 기존 링크 함수를 재사용했고, 없는 승인 기록을 생성하거나 내부 승인으로 대체하지 않았습니다. 실행한 로컬 시험과 미실행 실환경 확인을 구분했습니다.

## 배운 점·한계·다음 작업

- 승인자 목록 API가 있어도 결과에 연결 식별자와 읽기 권한이 없으면 발행 증거로 연결할 수 없습니다. 기관 상태·내부 승인·발행 서명·온체인 공동승인을 구분해야 합니다.
- 본부의 수정 전 트리 실측은 아래 인용했습니다. 이번 수정 후 브라우저 실측은 미실행이며 필요 시 본부 실측 요청입니다. 에이전트는 브라우저를 실행하지 않았습니다.
- C/B: 위 읽기 증거 계약 검토·연결 식별자와 체인 이벤트 증거 제공. A: 합의된 API 연결 후 실제 정상·누락·권한 거부·RPC 실패 확인. D: 독립 재현과 시연 수용 확인.
- 포트폴리오 설명 초안: 결과 카드 위에 떠 있던 단추를 정상 흐름으로 분리하고, 밝은 테마·키보드·체인 링크의 조건을 회귀 검사했습니다. 승인 기록은 권한과 연결 근거가 부족해 미제공 상태를 보존하고 후속 계약을 제안했습니다.

## 사실 확인

- 본인 확인: 사람의 확인 미수행. 2026-11-02 Codex 에이전트가 실행 기록과 diff에 근거해 작성했습니다.
- 작성자 외 리뷰어: 미지정·미실행. 실제 연결·다른 장비·clean clone·단계 전체 완료를 판정하지 않았습니다.

## 본부 실측 결과 (사용자 제공, 그대로 인용)

> 수정 전 트리, 헤드리스 Chrome, 예시 모드 금액 1원 변조 결과, 기술 증명 펼침. 320·375·1280px 어두운·밝은 모드 모두 로그인·테마 단추가 대화 스크롤 영역 위(스크롤 시작 y=60, 단추 아래 y=48)에 있어 겹치지 않았고 가로 넘침 0이었다. 실제 Tab 키 70회로 기술 증명, 시연 버튼, 입력창에 닿았고 Enter로 기술 증명이 열렸다. 비어 있을 때 보내기는 disabled라 Tab이 건너뛴다. 실서버·Sepolia 거래 링크는 미실행이다.

## 이번 재작업 완료 기준

- 충족: 착수 상태 확인·허용 경로 준수·기존 변경 보존, Etherscan 정상/거부와 대조 후 href 중복 방지, foldNarrow 경계값, 실제 HTML tabindex와 음수 사본 거부, 전체 예시의 내부 메모 미노출, 발행 서명 정상/실패/만료/권한 거부 및 비차단 표시, 지정 전체 시험·diff 검사·기록 정정.
- 미충족/미실행: 실서버·실제 Sepolia 거래 링크 연결 검증, 작성자 외 리뷰·clean clone 재현·W6 단계 전체 완료. 기관 등록·키 교체의 2-of-3 증거는 기존 API에 결과 연결 근거가 없어 미제공을 유지하며 발행 서명으로 대체하지 않습니다.
- 최신 감사 재작업 변경 파일: 페이지의 js/adapter.js, 시험의 op5_w6_demo.test.js, 이 기록. 다른 파일의 기존 미커밋 변경은 추가 수정 없이 보존했습니다.
- 최종 전체 시험 원문 요약:

```text
ℹ tests 388
ℹ suites 0
ℹ pass 383
ℹ fail 0
ℹ cancelled 0
ℹ skipped 5
ℹ todo 0
ℹ duration_ms 9624.289083
```

종료 코드 0. 로컬 전체 출력: `/private/tmp/op5-full-rework.log`(임시 실행 로그이며 영구 증거가 아님). 커밋·push·PR·병합·설치·외부 전송·브라우저 실행·PDF 생성은 하지 않았습니다.


## 최신 감사 재작업: 시험 공백 보완

- 기존 체인 링크 추가 경로를 그대로 보존했습니다. API 모드·Sepolia·유효 주소·hash 없음에서 주소 링크 1개로 시작하고, 체인 대조가 새 TX를 반환하면 2개가 되는지 검사합니다. 반복 대조에도 2개이며 거래 href·target=_blank·rel=noopener noreferrer를 확인합니다.
- 연결 전(샘플에 없는 Proof ID)·링크 없는 일반 문자 응답, 모든 예시의 buildCopyText도 미노출 검사에 포함했습니다. 사용자 원문과 원문 참조를 제외한 응답 표시 값을 검사하며 .html/.md/.png 및 docs/ 경로를 탐지합니다. 정상 example.com 도메인과 일반 예시 입력은 거부하지 않습니다. adapter 필터에는 .html만 추가했습니다.
- 변이는 저장소 파일을 바꾸지 않고 별도 Node 프로세스의 readFileSync 반환 문자열에서 주입했습니다. 실제 제품 코드는 유지했습니다. 정상 시험 43개 통과와 별도로 다음 변이가 회귀 시험에서 거부되는지 확인했습니다.

| 메모리 변이 | 실제 결과 | 종료 코드 | 실패 근거 |
| --- | --- | --- | --- |
| op5_connect.js 기존 230행 링크 추가 삭제 | 43 tests / 42 pass / 1 fail | 1 | 새 거래 링크가 없어 2개 기대 실패 |
| 연결 전 결론을 `이 시안은`으로 복원 | 43 tests / 42 pass / 1 fail | 1 | not_connected 표시 값 미노출 검사 실패 |
| 링크 없음 AI 칸을 `이 시안은`으로 복원 | 43 tests / 42 pass / 1 fail | 1 | no_reference 표시 값 미노출 검사 실패 |
| text_tools 복사 제목을 `(시안 · 예시 응답)`으로 복원 | 43 tests / 42 pass / 1 fail | 1 | normal 복사 글 미노출 검사 실패 |
| 화면용 예시 details에 `design/foo.html` 삽입 | 43 tests / 42 pass / 1 fail | 1 | normal 표시 값 경로 검사 실패 |

각 변이는 대상 소스에 실제 적용되었음을 확인했고 AssertionError로 실패했습니다. details 변이는 화면용 복사본의 details에 주입하여 필터 이후 표시 값 검사가 작동함을 확인했습니다. 원자료에 .html 경로가 있으면 adapter 필터에서 제거합니다. 기존 실제 HTML tabindex 음수 사본 2개 거부·foldNarrow 경계·서명 조회 실패 시험도 이번 지정 전체 명령에 포함되어 통과했습니다. 정상 전체 실행 후 기능 코드는 추가 변경하지 않았습니다. 최종 `git diff --check` 종료 0이며 지정 세 파일의 변경과 기존 미커밋 diff를 검토했습니다. 실서버·Sepolia·작성자 외 리뷰는 여전히 미실행입니다.
