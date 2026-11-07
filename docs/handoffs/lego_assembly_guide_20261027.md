# OriginProof 레고 조립 안내 (2026-10-27)

> 이미 끼워진 블록(✅)과 비어 있는 자리(❌)를 한 장에 모았습니다. 비어 있는 블록은 **꽂는 자리(파일:줄) · 맞는 모양(입력/출력 계약) · 다 됐는지 확인하는 법**만 맞추면 다른 블록을 건드리지 않고 끼울 수 있게 적었습니다.
> 기준: `phase/W6` + 블록체인 완성 브랜치(`feat/v5-w6-blockchain-completion`) + #63·#98 통합 시험(2026-10-27, 아래 "검증").
> 작성: A 김형준(대표 지시). AI 활용: Claude(claude-opus-5-5). 추정은 '추정'으로 표시.

## 0. 한눈에 보는 블록 지도

```
[웹 5안 apps/web-v5] ─HTTP(/api 프록시)─▶ [API apps/api] ─▶ [체인 어댑터] ─▶ [Sepolia Registry]
     ✅ 로그인·4축 보고서·체인 직접 대조        ✅ 신청·승인·발행·검증      ✅ 전환 RPC·projection   ✅ 배포·시연 데이터
                                               │
                                               ├─▶ ❌ [AI 분석 처리기] ◀─ ❌ [LLM 공급자: Claude/OpenAI]   (민서·인준)
                                               ├─▶ ❌ [이미지 입력 경로]                                (민서)
                                               ├─▶ ❌ [Track B 역조회]                                  (민서, #88)
                                               ├─▶ ❌ [회원가입 API]                                    (민서)
                                               └─▶ ⏸ [가스비 대납 Relayer] (향후)
```

| # | 블록 | 상태 | 담당 | 꽂는 자리 |
|---|---|---|---|---|
| 1 | Sepolia Wallet Registry 배포 | ✅ | B(대표 대행) | `packages/contracts/deployments/11155111.wallet.json` |
| 2 | API ↔ 체인 자동 연결·실행 중 RPC 전환·새 이벤트 projection·재조직 복구 | ✅ | B/C(대표 대행) | `apps/api/src/infrastructure/blockchain/wallet_deployment.py`, `wallet_failover.py`, `apps/api/src/originproof_api/projection.py` |
| 3 | 기관 신청→2-of-3 승인→발행→검증 API (실제 체인) | ✅ | C | `/v3/*` (`wallet_onboarding.py`, `wallet_governance.py`, `wallet_documents.py`) |
| 4 | 시연 데이터 스크립트 | ✅ | A | `scripts/fixtures/wallet_demo_flow.py` |
| 5 | 웹 5안(정적) | ✅ | A | `apps/web-v5/` |
| 6 | 복구·서비스 밖 독립 RPC 검증 도구 | ✅ | C(#63) | `scripts/verify_wallet_document.py` |
| 7 | 평가 자료(텍스트·이미지, 음성 보류) | ✅ | D(#94) | `fixtures/synthetic/`, `services/analyzer/src/originproof_analyzer/review_packet.py` |
| 8 | **AI 분석 처리기 연결** | ❌ | **민서(C)** | `apps/api/src/originproof_api/main.py:226` |
| 9 | **LLM 공급자(Claude 추가)** | ❌ | **인준(D)** | `services/analyzer/src/originproof_analyzer/providers.py:37` |
| 10 | 텍스트 입력 켜기 | ❌(설정) | 민서(C) | `settings.py:45` `wallet_text_input_enabled` |
| 11 | 이미지 입력 경로 | ❌ | 민서(C)+인준(D) | `wallet_analyses.py:210` `/v3/inputs` |
| 12 | Track B 역조회 | ❌ | 민서(C) | 이슈 #88 |
| 13 | RAG 수법 지식베이스·정량 지표 | ❌ | 인준(D) | `services/analyzer/` |
| 14 | 회원가입 API | ❌ | 민서(C) | 웹 `apps/web-v5/페이지/join.html` 이 기다림 |
| 15 | 가스비 대납(Relayer) | ⏸ 향후 | B/C | `settings.py:46` `wallet_relay_enabled`, `wallet_adapter.py:290` |
| 16 | 시연용 RPC 키·AWS 시연 서버 | ❌ | 대표 | `.env` (`API_BLOCKCHAIN_RPC_URL`) |

## 1. 끼워진 블록 (✅) — 그대로 쓰면 됨

### 1-1. Sepolia Registry
- 주소 `0xE540Bf29622AFFf40174B76992b016112f372A2e`, 배포 tx `0x9e40ba5f…a4bc`(블록 12001755). 승인자 #1 KISA 모델 `0x4f12…CA2a` · #2 금융보안원 모델 `0xE5d0…b240` · #3 통신 컨소시엄 `0x2Efd…eB1c`(모두 역할 모델, 실제 기관 아님).
- 배포·가스 주의(Sepolia 코드 저장 비용 상승 → `--gas-multiplier` 기본 800): [sepolia_deploy.md](../runbooks/sepolia_deploy.md).

### 1-2. API ↔ 체인
- 설정만으로 연결: `CHAIN_TARGET=sepolia`, `API_BLOCKCHAIN_RPC_URL`, `API_BLOCKCHAIN_RPC_FALLBACK_URL`, `API_WALLET_REGISTRY_ADDRESS`(+ manifest). 배포 기록·ABI·체인 위 CREATE·승인자 3명을 검증한 뒤에만 연결, 실패 시 503(가짜 성공 없음).
- 읽기는 주 RPC 실패 시 검증된 보조로 전환(쓰기는 주만). 새 이벤트 projection(확인 2블록)·재조직 자동 되감기.

### 1-3. 실제 체인 시연 (2026-10-27 Sepolia)
- `wallet_demo_flow.py --signer keystore`: 기관 활성(제안 EXECUTED 2/2) → 안내문 v1(154,000원)·v2(120,000원) 발행 → 검증 **VERIFIED / TAMPERED / SUPERSEDED**.
- 웹 5안을 같은 서버에 붙여 로그인·4축 보고서·체인 직접 대조(14항목 일치, Etherscan 링크)까지 확인.

### 1-4. 웹 5안 (`apps/web-v5/`)
- 실행: `node apps/web-v5/개발/op5-proxy.mjs` (기본 8790 → API 8000, 포트는 `OP5_PROXY_PORT`). 서버 없이 `apps/web-v5/화면 실행.command` 로 예시 모드.
- 웹이 서버에서 받는 값(AI 칸): `AnalysisReport`(`packages/python/originproof_core/wallet_contract.py:425`)의 `risk_level`, `evidence[].quote/start_offset/end_offset/rule_id/source`, 실패 코드(`ANALYZER_UNAVAILABLE`, `ANALYSIS_TIMEOUT` 등). 분석기가 연결되면 오른쪽 'AI 위험 설명' 칸과 형광펜이 그대로 채워짐.

## 2. 비어 있는 블록 (❌) — 꽂는 법

### 블록 8. AI 분석 처리기 연결 — 민서(C)
- **꽂는 자리:** `apps/api/src/originproof_api/main.py:226` `app = create_app()` → `create_app(analysis_processor=...)`(인자는 `main.py:86`, 저장 `main.py:157`, 사용 `wallet_analyses.py:152-163`).
- **맞는 모양(이미 있음):** `services/analyzer/src/originproof_analyzer/phishing.py:136` `PhishingAnalyzer` 가 바로 "C's async analysis_processor(text) callback"입니다. `async __call__(text: str) -> AnalysisReport`. 결과는 API가 `ground_report`(`wallet_analyses.py:66`)로 원문 근거 위치를 다시 대조합니다.
- **먼저 정할 것(C·D 합의):** API 패키지는 analyzer 를 의존성으로 선언하지 않았습니다. ① analyzer 를 API 안에 묶어(in-process) 부를지, ② analyzer 를 별도 서비스로 두고 HTTP 로 부를지 먼저 정합니다(기존 analyzer HTTP 엔드포인트는 카드 안내 추출용이라 피싱 분석용 경로는 없음). 상세: [AI 연결 인계서](a_ai_connect_handoff_20261027.md) 2절.
- **해야 할 일(①을 고른 경우):**
  1. `PhishingAnalyzer(settings=AnalyzerSettings())` 를 만들어 `create_app(analysis_processor=…)` 에 넘기기(공급자는 블록 9의 설정으로 고름, 기본 mock).
  2. API 도커 이미지가 analyzer 패키지를 포함하도록 `infra/docker/api.Dockerfile`(현재 `services/analyzer` 미포함)·`PYTHONPATH`·uv 패키지 의존 정리(추정: analyzer 의 openai 의존이 API 이미지에 필요).
  3. `API_WALLET_TEXT_INPUT_ENABLED=true`(블록 10, `settings.py:45`).
- **확인:** Mock 공급자로 `POST /v3/inputs`(TEXT) → `POST /v3/analyses` → `GET /v3/analyses/{id}` 가 `COMPLETED` + `report.risk_level` 을 돌려주고, 처리기를 빼면 `ANALYZER_UNAVAILABLE`. 기존 `apps/api/tests/test_wallet_analyses.py` 통과. 기준선 시험: `apps/api/tests/test_ai_connect_readiness.py`(Mock 주입 HTTP 4건: 정상·D 보류·C 인용 변조 거부·C 위치 변조 거부). 생산 연결 뒤에는 Settings 만으로 같은 결과가 나와야 함.

### 블록 9. LLM 공급자(Claude 추가) — 인준(D)
- **꽂는 자리:** `providers.py:37` `class LLMProvider(Protocol)` 의 `async analyze_phishing(text) -> AnalysisReport | dict`(`providers.py:45`). 기존 구현: `MockLLMProvider`(`:136`), `OpenAILLMProvider`(`:251`). 선택은 `PhishingAnalyzer.__init__`(`phishing.py:139-147`)의 `settings.llm_provider`.
- **해야 할 일:** `AnthropicLLMProvider` 를 같은 계약으로 추가하고 `llm_provider == "anthropic"` 분기 추가. 키는 **서버 `.env` 에만**(예: `ANALYZER_ANTHROPIC_API_KEY`, 이름은 D 가 확정). 출력은 구조화 JSON → `AnalysisReport` 검증. AI 는 진위 판정 금지(위험 설명만).
- **크레딧:** 대표 Claude Max 의 월 API 크레딧(Console 조직 연결 후) 사용 가능. 시험은 Mock 으로 통과시키고, 실제 호출은 대표 허락 뒤 소량.
- **확인:** Mock/기록 응답으로 기존 analyzer 시험 + 새 공급자 시험 통과, 실제 호출 0(허락 전).

### 블록 11. 이미지 입력 경로 — 민서(C)+인준(D)
- **꽂는 자리:** `wallet_analyses.py:210` `/v3/inputs` 는 지금 `TextInputRequest`(TEXT)만 받음. 이미지(DOCUMENT_IMAGE) 업로드 접수 추가 필요.
- **맞는 모양:** analyzer `SemanticInput` 은 PNG·JPEG·WebP(5MB)를 받음(이슈 #92). 웹 5안은 사진 사전 검사(`apps/web-v5/페이지/js/op5_media.js`)까지 되어 있고 업로드 경로만 기다림.
- **주의:** 사진 판독 오류는 진짜 안내문을 "원본과 다름"으로 보이게 할 수 있음 → 판독한 값과 판독 한계를 함께 보여 줄 것. QR·검증 코드가 있는 사진(Track A)부터.

### 블록 12. Track B 역조회 — 민서(C), 이슈 #88
- 코드 없는 문자에서 [기관 + 수신자 해시/발송일 + 금액·계좌] 조합으로 원본 찾기. 없으면 UNVERIFIED + AI 위험 분석. 여러 건이면 모호함 표시(지어내지 않음).

### 블록 13. RAG·정량 지표 — 인준(D)
- JSON 수법 지식베이스(20~30개, 수법 ID) → AI 근거에 `matched_technique_ids` 로 연결(웹은 이미 "공개 피싱 수법 ID" 자리를 표시). 정답셋 30~50건으로 추출 정확도·근거 적중률·오탐지율.

### 블록 14. 회원가입 API — 민서(C)
- 웹 `join.html` 은 개인/기관 선택·약관 동의·(개인) AI 키 기기 암호화 저장까지 하고 "서버 가입 기능 연결 전" 안내를 보여 줌. `POST` 가입 엔드포인트가 생기면 연결.

### 블록 15. 가스비 대납 Relayer — 향후
- 지금은 **기관 지갑이 직접 거래를 보내고 가스비를 냄**(`wallet_relay_enabled=false`, 어댑터 `submit` 은 503). 웹 배지도 이에 맞게 정정함. 만들 경우 서버가 가스비 지갑 키를 관리해야 하므로 별도 설계·승인.

## 3. 조립 순서 (권장)
1. 블록 8 + 10(민서) → Mock 공급자로 웹 AI 칸이 채워지는지 확인.
2. 블록 9(인준) → 같은 자리에 Claude 공급자 꽂기, 실제 호출은 소량.
3. 블록 11 → 사진(QR 있는 안내문)으로 확인.
4. 블록 12·13·14 → 남는 시간에.
5. 11/3 코드 동결 전 RC 리허설.

## 4. 검증 (이 문서 기준 통합본)
- 통합 시험 브랜치 = 최신 `phase/W6` + #63 + #98 + 블록체인 완성 브랜치: 충돌 0.
- `ruff` 통과 · `pytest -q` 1357 passed / 19 skipped · `forge test` 101 passed · `make security` 0건 · `make generate` 차이 없음 · 검토본 `--check` 일치.
- 실제 Anvil: 배포·RPC 전환 2 passed, 실제 API 프로세스 8 passed.
- 실제 Sepolia: 위 1-3.

## 5. 남은 위험
- 공개 RPC(publicnode)가 자주 실패 → 시연 당일 키 RPC(Alchemy/Infura) 권장.
- 웹 5안은 정적 사이트(`apps/web-v5`), 기존 Next.js `apps/web` 과 별개. 어느 쪽을 시연 기준으로 할지 팀 결정 필요.

## 6. 함께 올린 것
- [AI 연결 인계서](a_ai_connect_handoff_20261027.md)와 기준선 시험 `apps/api/tests/test_ai_connect_readiness.py`(엑스맨 작성, 클린트 감사 통과, 생산 코드 변경 없음).
- 웹 5안 `apps/web-v5/`(가스비 배지·과장 문구 정정 반영).
