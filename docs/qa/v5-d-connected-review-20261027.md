# D PR 코드 리뷰·실제 연결 검증 — 2026-10-27

담당 D 여인준 `yijun0330`, Codex 리뷰·수정·실행 보조. 사용자님의 “PR 코드 리뷰랑 연결 검증도 다 해” 지시와 추가3회 직접 승인을 적용했습니다. 계획5.1 / v5-shared-0.2 / V5-W5-D·W6-D. 기존 [PR #100](https://github.com/OriginProof-3web/OriginProof/pull/100) source `cc09ebf`·사용자 변경·.env·개발48회/최종36회 기록을 보존했습니다.

## 리뷰 범위와 판정

- #99의 고정 **`c325cf00e2a769c3186222c3859d285d911f8685`**를 별도 detached 검증 폴더로 읽고, 수정은 새 `codex/v5-w6-d-connected-review` branch에만 기록했습니다. #99/phase/integration을 원격 병합·수정하지 않았습니다.
- 코드 리뷰: 체인/배포/증거·RPC 전환·projection/reorg·API lifecycle, 웹 인증/프록시/보고서·입력 실패, 기존 D 소비와 실제 실행 경계를 확인했습니다. 생성 bundle/예시 자료를 별도 보안 인증으로 평가하지 않습니다.
- #100의 이미지 evaluator·오류 분모·동일 deadline·callback 정답 비전달·정책false와 동결 평가 기록도 검토했습니다. **자가검토이며 다른 사람/소유자 코드 승인으로 기록하지 않습니다.**
- 확인한 P2 네 항목은 아래와 같고 새 D 수정 PR로 제공합니다. 제품 기본 AI 주입/이미지 업로드 미구현은 #99가 명시한 미연결 범위이며 새로 생긴 회귀로 오인하지 않습니다.

| ID | 재현된 문제 | 수정·검증 |
| --- | --- | --- |
| DCR01 | 새 실제 failover 검사에서 Unix socket pg_isready가 initdb 임시 서버를 준비 완료로 오인. 최초 실제9개 중8 PASS/1 FAIL(`connection_lost`) | TCP `-h 127.0.0.1` 확인. 나머지 실제 assertion 유지. 최종 **9/9 PASS** |
| DCR02 | 실제 OpenAI 보고서를 받은 화면에 “서버 분석기·RAG 연결 전”이 계속 표시 | 완료 보고서/규칙 fallback/기록 응답/예시/미연결을 별도 caption으로 표시. 단위+실제 브라우저 replay 확인 |
| DCR03 | 명시적 demo 장면도 실제 `/auth/me`를 읽고 비회원 응답이 simulated API 모드를 예시로 돌림 | 유효 scene을 먼저 읽고 그 장면에서만 실제 세션 조회/회원 guard를 생략. 일반 회원/세션 만료 거부는 유지 |
| DCR04 | 가져온 테스트의 외부 설계 경로·미커밋 캡처·구형 auth/HTML snapshot 때문에10 FAIL | PNG CLI 검사는 합성 임시 파일로 재현하고 실제 화면 캡처라고 부르지 않음. V1 문구는 현행 A 구현의 회귀 snapshot으로 고정(외부 원본 설계표 승인/동등 확인 아님). 상태를 checks에서 재계산하지 않는 invariant·bundle hash·일반 인증 거부 유지 |

기존5안 Node 검사115 PASS/10 FAIL/6 SKIP → 수정 뒤 **126 PASS/0 FAIL/6 SKIP**(신규 caption 검사1개 포함)입니다. skip6은 기존 가져온 web-2 전용 화면/모듈 정적 검사이며 바꾸지 않았습니다. 이 묶음을 Quality Gate에 추가했습니다. D의3회 request budget guard는6개 mock 검사로 별도 CI 연결했고 실제 OpenAI를 호출하지 않습니다.

## 같은 환경에서 실행한 실제 연결

실제 실행 source **`e4611213ac514ae445345f3699e6c35d9ee1ea85`**, 일회용 PostgreSQL16.4·별도 uvicorn·실제 Anvil1.4.4·#99 자동 Registry connector·5안 Node 프록시·Chromium입니다. 기존 데모 DB/공개 체인을 초기화하거나 쓴 적이 없습니다. 테스트가 만든 컨테이너/서버만 정리했습니다.

1. 기본 처리기 없는 설정: 로그인→TEXT 접수→분석이 **FAILED / ANALYZER_UNAVAILABLE**인 것을 실제 TCP로 재현했습니다. 건강 검사200이 AI 연결 완료를 뜻하지 않음을 확인했습니다.
2. 실제 Anvil 계정/Registry·API로 기관 신청→데모 메일·내부 승인→키 증명→2-of-3 승인→안내 v1/v2 발행. 정상 v2 `VERIFIED`, 금액1원 변조 `TAMPERED`, 과거v1 state `SUPERSEDED`를 확인했습니다. A의 `wallet_demo_flow.py`와 B/C 구현을 재사용했으며 D가 새로 구현한 발행 기능으로 합산하지 않습니다.
3. D QA composition에 기존 `PhishingAnalyzer`를 명시적으로 주입했습니다. 실제 브라우저 로그인→프록시→`/v3/inputs`→`/v3/analyses`→폴링→공통 report→4축 화면/근거 강조를 mock/rule fallback과 실제 OpenAI 각각에서 확인했습니다. 두 브라우저 실행 모두 **COMPLETED/HIGH·page error0**입니다. 참조 ID 없는 합성 문자이므로 공식 기록 축은 확인 불가이며 AI가 진위를 만들지 않았습니다.
4. 승인한 문서1개(DP-H01)를 **인증된 loopback QA 전용** `/__d_qa/document`에서 판독→기존 텍스트 분석으로 연결했습니다. 판독47/47자 일치(CER0), HIGH, RULE+LLM 근거. **1개 smoke이며 이미지23개 품질 평가/픽셀 정확도/제품 업로드 완료가 아닙니다.**
5. 제품의 `/v3/inputs`에 `DOCUMENT_IMAGE`를 보내면 **422**입니다. 검증용 bridge는 공통 API/Schema에 등록하지 않았고 실제 제품 경로라고 소개하지 않습니다. 기본 `app=create_app()`도 이번 QA 때문에 바꾸지 않았습니다.

### 유료3회 보존

사용자 직접 답변 **“연결 검증용 추가 3회 승인”**, 기존84회와 구분합니다. 텍스트1 + 이미지 판독1 + 판독문 분석1 = **3 HTTP200 / retry0 / 사용량 누락0 / 출력 초과0**. 현재 누적 모델 요청87회입니다(텍스트 최종36 재평가 아님).

| 단계 | 출력 상한 | 입력 / 출력 / 총 usage |
| --- | --- | --- |
| TEXT_SMOKE | 1024 | 904 /140 /1044 |
| IMAGE_CONVERSION | 4096 | 412 /101 /513 |
| IMAGE_ANALYSIS | 1024 | 913 /145 /1058 |

총 usage **입력2229/출력386/합계2615**. 비용/청구액은 조회·추정하지 않았습니다. 요청 전 단계/횟수 예약, 4번째 거부, 사용량 미확보·HTTP 실패·알 수 없는 결과 뒤 중단을 보존합니다. 기존 CappedTransport를 재사용하고 원시 모델 응답·키를 Git/로그에 쓰지 않았습니다. 새 journal은 기존 D worktree의 Git 제외 `build/private/v5-d-connected-smoke-20261027.json`(0600)이며 종료 후 journal과 운영 정책 모두false입니다. 이전84회 journal hash도 불변입니다. 실제 실행을 다시 보내지 않았습니다.

### 화면 근거와 수정 검증

[실제 모델 연결 화면(문구 수정 전)](assets/v5-d-connected-20261027/actual-live-before-caption-fix.png)은 위 실제 브라우저 결과입니다. 연결되었는데 “연결 전”이라고 표시한 DCR02를 보여 줍니다.

[수정 후 desktop](assets/v5-d-connected-20261027/caption-after-controlled-replay.png), [320px](assets/v5-d-connected-20261027/mobile320-controlled-replay.png)는 **추가 모델 요청0인 통제된 UI replay**입니다. 실제 연결 재실행/모델 품질로 합산하지 않습니다. caption “서버 보고서”, 320px scrollWidth320·가로 넘침false를 확인했습니다. 전체 접근성/실제 휴대폰 QR 완료를 주장하지 않습니다.

## 검사·재현

기능 source **`73bea7c9ab9749934f2bfd3173f8eb93c097f3c2`**의 키 없는 git archive에서 기본 **1361 PASS/19 SKIP/기존 Starlette 경고1**, 생성기5종 차이0입니다. 뒤 `05d7953`은 CI의 lint/경로 등록만 추가했습니다. 같은 노트북/기존venv를 재사용했으며 다른 실제 장비 재현이 아닙니다. 새 외부 패키지/lock·계약/ABI/Schema를 변경하지 않았습니다. Foundry는 기존 고정1.4.4 공식 archive digest를 대조해 임시 도구 경로에만 준비했습니다.

- 실제 배포·failover/projection·API 프로세스9 PASS, 계약101 PASS. 기본 opt-in skip과 별도 실제 실행을 구분합니다.
- 새 과금 가드6 PASS(mock/네트워크 차단), Node126 PASS/6 기존SKIP, 전체 Ruff·문서/JSON·변경 파일 검사.
- 최초 전체 기본 검사는 loopback bind 권한 제한으로 TCP 로그 검사1개가 실패했습니다. 소스/assertion을 완화하지 않고 로컬 포트를 허용한 환경에서1361 PASS를 확인했습니다.
- 최초 검증 실행기의 로컬 배포 receipt는 아직 채굴 전None이었습니다. 기존 테스트의 receipt 대기 방식을 재사용해 수정했고 그 시도에서는 모델 호출0이었습니다. clean-source 생성물 점검기는 Git의 한글 경로 quoting을 파일명으로 오인해 실패했으며 `git ls-tree -rz`로 고쳐 5종 생성물 차이0을 확인했습니다. 이들은 제품 성공으로 합산하지 않습니다.

```sh
export PATH=/path/to/fixed-foundry-1.4.4:$PATH
export PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src:apps/api/tests:fixtures/finals:scripts/fixtures
python -m pytest -q fixtures/finals/test_v5_d_connected_smoke_budget.py
ORIGINPROOF_WALLET_LIVE=1 python -m pytest -q apps/api/tests/test_wallet_deploy_live.py apps/api/tests/test_wallet_failover_live.py services/indexer/tests/test_wallet_api_process.py
node --test apps/web-v5/시험/*.test.js apps/web-v5/시험/*.test.mjs apps/web-v5/시험/가져온/*.test.js apps/web-v5/시험/가져온/regression/*.test.js
```

`fixtures/finals/v5_d_run_connected_smoke.py`는 **실제3회를 이미 소진한 수동 QA 실행기**입니다. 현재 정책false와 기존journal 존재로 재실행을 막습니다. 새 호출 승인으로 해석하지 마세요. API 이미지·서비스 API를 새로 구현한 도구가 아니며 CI는 mock budget 검사만 실행합니다. `.env`·테스트 계정/세션 파일은 결과 자료에 포함하지 않았습니다.

## 공개 Sepolia 직접 읽기와 정확한 미해결

공개 RPC를 서비스 API 없이 직접 읽었습니다. manifest/커밋 ABI·chain ID·현재 배포 block/runtime snapshot은 통과했습니다. 이어 canonical CREATE·constructor 승인자 검증에서 **배포 시점 `eth_getCode`가 HTTP200 + JSON-RPC -32000**을 반환해 완료하지 못했습니다. 코드·승인자를 검증하지 않은 성공으로 바꾸지 않았고 공개 거래 쓰기는0입니다. 원본/서명 자료 공개 검증 패키지도 인계되지 않아 문서 전체의 독립 서명 확인은 미실행입니다. [메서드/오류 코드·전체 증거 JSON](v5-d-connected-review-20261027.json).

| 담당 | 이제 필요한 정확한 인계 |
| --- | --- |
| C | 검증된 기존 in-process callback을 제품 기본 엔트리포인트·배포/설정/수명주기에 연결. 제품 이미지 업로드/receipt·소유권·보관·변환문/근거 계약 구현. D QA bridge를 제품 API로 복사해 확정 계약으로 간주하지 않음 |
| A/C/B | 이 리뷰 수정 PR을 소유 경로 기준으로 검토. 실제 연결 통과·코드 리뷰와 타인의 GitHub 승인/병합을 구분 |
| B/C | 과거 배포 블록의 eth_getCode를 지원하는 안정 RPC와 공개 원본·서명·배포 참조 패키지. 키는 채팅/문서로 요청하지 않음 |
| 팀 | 다른 실제 노트북과 동일 RC 리허설3회·제출 조건. 같은 장비의 archive를 다른 장비 성공으로 대체하지 않음 |

G07은 RESOLVED_LOCAL_LEGACY 유지, 음성/STT·Claude/RAG·Decisions 추가 구현은 하지 않았습니다. PR #100의 최종36 결과를 수정하지 않았습니다. 코드 리뷰·로컬 실제 연결 검증을 수행했지만 W6 전체 단계·제품 이미지 지원·원격 병합 완료로 판정하지 않습니다.
