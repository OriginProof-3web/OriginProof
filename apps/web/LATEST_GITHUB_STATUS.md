# 최신 GitHub 확인 — 2026-10-04 / A 김형준

확인 branch `codex/admin-latest-functions`, 시작 `576832905cb50e8e29873a89d891f48706ea8f2d`, 시작 worktree clean.
`git fetch origin` 및 gh PR 원본을 확인했습니다. 최신 제품 API #38은 `3ef1fd4` 그대로이며 교체하지 않았습니다.
새 원격 변경은 D W4 실행 준비와 W5 후보 QA/문서입니다. 타인 branch checkout/merge나 제품 코드 수정은 없습니다.

## 개인 완료와 단계 완료

| 단계 | A 개인 근거 | 남은 완료 조건 |
| --- | --- | --- |
| W1 | #27 승인·병합 | 팀 phase/W1 → integration #39 Draft 유지. 개인 병합과 팀 단계 승격 분리 |
| W2 | #28 승인·병합 | #51 기존 phase/W2 브라우저 6 passed/6 failed. 활성화·키 GET/등록/폐기·ACTIVE 문구·definition-list 접근성 수정과 해당 SHA 재검증 필요 |
| W3 | #44 승인·병합, #48 QR·최신 실제 연결 검사·CI 통과 | #48 작성자 외 reviews 없음·OPEN, D QR 독립 재현/같은 최종 SHA 검사 대기 |
| W4 | 관리자에서 키 교체·Proof 폐기·consume 실제 연결 19개, 웹 22/13 이전 검사 | 웹 단계 PR/리뷰·D3 독립 브라우저 12개 NOT_RUN. 일반 기업/개인 이식은 사용자 결정한 관리자 검증 뒤 수행 |
| W5 | 관리자 오류/복구·작업·체인 조회 부분 구현 | W5-A1/A2/A3 전체 오류/접근성·문구·세 역할 같은 통합 SHA 인계, D2 15개 NOT_RUN. phase/W5 없음 |
| W6/W7 | 관리자 UNKNOWN 동일 tx 복구의 부분 근거 | 전체 장애 화면/독립 환경/시연 대본·발표·RC 미완료. 일부 복구 통과는 단계 완료가 아님 |

가장 이른 미종결은 W2 실제 웹 수용 조건입니다. W3 구현·검사와 W4 관리자 선행 작업이 진행되어도
주차 전체가 연속 완료된 것으로 집계하지 않습니다. 예전 W2 화면 결함은 최신 관리자 구현 결과만으로 닫지 않습니다.

## 최신 팀원 PR

- [#49](https://github.com/OriginProof-3web/OriginProof/pull/49) `f2e9774`: W4 D1/D2와 D3 준비. D 보고의 21 실제/core QA 통과와 브라우저 12 NOT_RUN을 구분합니다.
- [#50](https://github.com/OriginProof-3web/OriginProof/pull/50) `7e75986`: nonce 예약 cleanup OPEN. 아직 phase/W2 병합 전이며 관리자 #38에 이 변경이 포함됐다고 주장하지 않습니다.
- [#51](https://github.com/OriginProof-3web/OriginProof/pull/51) `17f78e3`: W2 실제 브라우저 6 통과/6 실패. 기본 CI 성공은 이 실패 해결이 아닙니다.
- [#52](https://github.com/OriginProof-3web/OriginProof/pull/52) `ff1d4e7` Draft: W5 문서, QA 코드 별도 `a3f55c6`. 팀원 보고 fresh18 PASS, mixed17 PASS/1 FAIL.
  G07: 추가 Anvil 재기동 후 Reader UNAVAILABLE, 원인/제품 결함 여부 미확정, B/C 확인 후 D 재검사.
  G01 통합 SHA, G02 W2 UI, G03 QR, G04 W4 D3, G05 접근성/감사, G06 체인 경계, G07 장애가 남습니다.

## 이번 관리자 업데이트와 직접 검사

`official/github-update.json`에 gh 확인 시각·고정 SHA·상태·미완료를 보존하고 관리자 검사 결과 메뉴에 표시합니다.
D 보고를 이 로컬 실행 결과로 복제하거나 PASS 처리하지 않습니다. #49 직접 재실행 버튼을 추가했습니다.
새 프레임워크/의존성/유료 AI/기존 DB reset/외부 게시/PR/push는 없습니다. 관리자 디자인과 기존 기업/개인 화면은 유지합니다.

- #49 frozen archive 정책 QA: **20 passed / 1 skipped**. opt-in 실제 DB/체인 1개는 이번 실행에서 제외, D3 브라우저 미실행.
- 웹 lint, JS build/admin scripts 구문, Python 구문, diff 검사 통과.
- 이번 변경은 제품 API 갱신이 아닌 최신 검증·진행 상태와 검사 실행기 갱신입니다.
- 상세 #49 실행 시각/명령/개별 결과는 기존 관리자 `collaboration-results.json`에서 확인합니다.
- 이전 관리자 19개/API404개/웹22·13개는 2026-10-03 결과로 보존하며 이번 날짜의 새 전체 실행으로 표현하지 않습니다.

## 이번 로컬 장애（2026-10-04）

기존 Anvil 중단 후 native JSON이 잘려 재기동 실패했습니다. RPC backup 복원을 시도했으나
대용량 restore가 기본 2MB 한도에 막혔고, 기존 준비기의 finally가 실패 때에도 checkpoint를 기록해
실패 체인의 빈 snapshot을 쓴 결함을 확인했습니다. 손상 원본을 private 보존하고 완전한
block/accounts/blocks/transactions와 2282개 historical state 항목을 복구했습니다.
마지막 불완전한 과거 state는 복구하지 못했으며 기존 DB/서명기/계정은 reset하지 않았습니다.
팀원 G07과 같은 원인이라고 단정하지 않습니다.

관리자 runtime은 준비 성공 때만 checkpoint, 60초 atomic RPC checkpoint와 loopback Anvil의
대용량 restore 허용으로 고쳤습니다. 5초 native 반복 dump를 제거하고 중복된 이전 관리자 runtime을
종료했습니다. 8770 일반 웹 runtime은 유지했습니다. 실제 rotate API로 두 기관 새 키가 CONFIRMED입니다.
초기 관리자 브라우저는 체인 미준비 timeout/발행 거부로 실패했습니다. 일부 통과 뒤 준비 예외가
전체 passed로 잘못 기록되는 결함도 수정했습니다. 준비 실패 checkpoint 보존 unittest 1개 통과입니다.
완전한 과거 chain state 복구나 전체 단계 완료를 주장하지 않습니다.

최신 Git 상태 표시 브라우저 검사 1 passed(8768 실제 운영자 로그인·관리자 메뉴·팀원 결과 구분).
복구 직후 일반 발행은 UNKNOWN receipt를 반환하여 전체 검사가 실패했습니다. 성공으로 변환하지 않았습니다.
5초 주기 블록 + 실제 쓰기 automine을 관리자 합성 runtime에 적용하고 UNKNOWN 장애 주입 검사는 별도 유지합니다.
과거 state 일부 누락 한계는 유지합니다.

### 이번 최종 결과

#49 정책 20 passed/1 opt-in skipped, 최신 상태 표시 브라우저 1 passed, 준비 실패 보호 unittest 1 passed, lint/구문/diff 통과.
전체 관리자 실제 연결은 **7 passed/1 failed 후 중단**: 은행 중지 상태 재조회에서 CHAIN_UNAVAILABLE.
그 전 신규 발행·등록·검증·비교·권한·consume·폐기·키 교체는 기록된 실제 범위로만 통과입니다.
기관 재활성화 정리 요청도 CHAIN_OR_SIGNER_UNAVAILABLE(503)로 실패했습니다. 복귀 성공으로 표시하지 않습니다. 검사 실패에도 finally에서 복귀 요청을 시도하도록 보완했습니다.
전체 관리자 브라우저도 초기 체인 장애로 실패했으며 최신 상태 표시 검사 1개가 전체 E2E 통과를 대신하지 않습니다.
현재 API health ready 200은 전체 기능 검사의 성공이 아닙니다. 남은 로컬 체인 역사/재조회 장애는 미해결로 보존합니다.
기업·개인 이식과 새 push/PR은 하지 않았습니다. 이전 2026-10-03 관리자19/API404/웹22·13 결과와 합산하지 않습니다.

## 2026-10-04 오류 복구와 기업·개인 이식

사용자 요청으로 관리자 검증 후 일반 기업·개인 화면에도 lifecycleEnabled를 전달했습니다.
기업: 키 생성/교체/폐기, Proof 발행/등록/폐기, 허가된 사용, Operation 조회/같은 거래 복구.
개인: ID 조회/내용 비교, 지정 수신자 1회 사용, 미확인 거래 조회/복구.
관리자 전용 기관 운영 권한이나 합성 역할 전환은 일반 페이지에 노출하지 않습니다.
일반 QR는 기존 공개 ID 링크이며 관리자 QR는 별도 관리자 조회 링크를 유지합니다.

8768 `/api`와 관리자 역할 proxy는 동일 C #38 고정 SHA의 8780 API를 사용합니다.
이전 8770의 데이터는 삭제하지 않았으며, 과거 일반 페이지에서 발행한 ID는 이전 환경 기록입니다.
기관/계정 ID를 보존하고 로컬 보호된 기존 테스트 계정의 로그인 정보를 8780 합성 DB에 반영했습니다.
역할·기관 불일치가 있으면 seed를 거부합니다. 브라우저 역할 값으로 권한을 부여하지 않습니다.

오류 원인/수정:
- 전체 과거 storage snapshot의 반복 dump가 RPC를 5초 넘게 막아 Reader ReadTimeout/503을 만들었습니다.
  현재 storage·블록 정체성·receipt를 60초마다 atomic 저장합니다. 원래 역사/손상 파일은 보존합니다.
- Anvil interval 설정은 automine을 끕니다. interval 0을 먼저 지정하고 automine true를 나중에 지정합니다.
  빈 블록 무한 채굴을 제거하고 쓰기를 즉시 채굴합니다. UNKNOWN 시에는 새 요청 대신 기존 tx를 복구합니다.
- API/Analyzer를 다시 시작하고 health ready/live를 확인했습니다.
- 관리자 권한 확인은 매 요청 실행하며 요청 제한을 줄이지 않습니다. 기능 검사는 1.2초 간격,
  관리자 실제 변경 검사와 브라우저 검사는 같은 합성 환경에서 순차 실행합니다.
- `.command` 시작은 index.html을 유지하고 API 또는 mock Analyzer가 없으면 최신 runtime을 기동합니다.

재시작 후 관리자 실제 검사 19 passed(2026-10-04T08:05:48Z), 컴포넌트 22 passed,
checkpoint/채굴 복원 순서 unittest 2 passed, lint/typecheck/build 통과.
기업/개인 브라우저 최종 결과는 아래에 기록합니다.
현재 상태 checkpoint는 전체 과거 블록 storage replay를 보장하지 않으며 W5 D 장애 검사를 대신하지 않습니다.
공개 회원가입·새 두 유형 AI 추출 API·운영 배포·D 독립 재현/PR 승인은 이번 완료 범위가 아닙니다.

### 이식 후 최종 확인 (2026-10-04)

- 기존 8768 관리자 화면 → 실제 PostgreSQL/로컬 Anvil 기능 검사: 19 passed (AI 후보 추출만 mock).
- 기업·개인·관리자 브라우저: 최종 15개 사례 통과. 전체 실행은 13 passed/2 failed였고,
  지급 요청 탭의 아이콘을 포함한 접근성 이름과 이력 목록 선택자를 수정한 2개 재검사는 2 passed였습니다.
  단일 실행에서 15개 모두 통과했다고 기록하지 않습니다. 실제 API 연결 5개, 나머지는 디자인/합성 API 회귀입니다.
- 기업 실제 발행·공개 QR 디코딩·타 기관 내용 조회 거부·키 교체/이전 키 유지·작업 이력 확인,
  개인 정상 비교·변조·1회 사용 및 재조회, 문서 폐기의 개인 화면 반영을 확인했습니다.
- 컴포넌트 23 passed; 런타임/채굴 복원/운영자 권한/429 구분 unittest 5 passed.
- lint/typecheck/운영용 build/Python compile/diff 확인 통과.
  임시 Next 생성물의 중복 `* 2.ts`로 발생한 타입 오류는 해당 생성 캐시만 제거해 해결했습니다.
- 관리자 권한 확인에서 API 429/503을 403으로 오인하지 않습니다. 요청을 자동 재전송하지 않습니다.
  관리자 결과 polling은 10초 간격이며 실제 변경 suite와 브라우저 suite는 동시에 시작하지 않습니다.
- 기존 `.command`는 index.html 시작을 유지하며 준비 검사는 현재 API의 18546 체인을 확인합니다.
- 실행 웹: 576832905cb50e8e29873a89d891f48706ea8f2d + 로컬 변경.
  API: C #38 3ef1fd40943914c1450e8bc05047119ab7eabbc0.
  결과와 웹 fingerprint는 기존 관리자 `검사 결과`에 저장했습니다.
  최초 브라우저 실패 원본은 `/tmp/originproof-web-full-final-attempt.xml`,
  재검사 원본은 `/tmp/originproof-web-final-rerun.xml`입니다.

새 PR/push/리뷰 승인/운영 배포는 하지 않았습니다. W4의 담당 웹 연결 후속은 구현·로컬 검사 완료이며,
phase PR·작성자 외 리뷰·D 독립 재현·팀 전체 단계 완료는 별도입니다.
이전 8770 DB/18545 체인 데이터는 보존합니다. 현재 `/api`의 과거 ID 조회는 8780 환경에 저장된 기록을 사용합니다.
공개 회원가입, 지급 요청/공식 문서 AI 추출, 외부 운영 배포는 서버 계약/별도 수용 기준 대기입니다.
