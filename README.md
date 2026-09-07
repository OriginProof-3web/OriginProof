# OriginProof — MVP 개발 가이드 (팀 내부 문서)

> OriginProof 2일 MVP를 네 명(M1~M4)이 Codex 또는 Claude Code와 함께
> **동일한 구조, 동일한 계약, 동일한 환경**에서 개발하기 위한 내부 가이드.
>
> 사용법: 공통 규칙(1~18장)을 전원이 먼저 읽고, 이후 자신의 역할(M1~M4) 섹션(19~22장)만 읽어도
> "무엇을 만들어야 하는지" 알 수 있도록 역할별 정보(Branch, 담당 경로, 금지 경로, 구현 항목, 테스트, 완료 조건, Agent Prompt)를
> 각 섹션에 모아두었다.

> **MVP 완료 상태 (2026-09-08):** `mvp/integration@a1a671b`에 M1~M4 구현과 통합이
> 완료되었습니다. `make demo`와 `make mvp-test`는 호스트 Foundry 없이 두 독립 개발
> 환경에서 재현 검증을 통과했습니다. 아래 체크리스트와 통합 순서는 MVP 진행 당시의 기준 기록입니다.

---

## 1. 전체 흐름 요약

```
M1 Bootstrap
    ↓
공통 Repository 구조 생성
    ↓
Bootstrap Commit 확정 → Commit SHA 공유
    ↓
네 명 모두 동일 SHA 확인
    ↓
각자 MVP Branch 생성 → 담당 영역 병렬 개발
    ↓
PR → 교차 검증 → mvp/integration
    ↓
MVP E2E
```

최종적으로 하나의 흐름이 연결되어야 한다:

```
Origin Mock Bank Proof 발행
        ↓
카드 결제 문자
        ↓
M2  AI 필드 구조화
        ↓
M1  Signed Proof 조회
        ↓
M4  Blockchain Reader
        ↓
M3  Registry Trust State 확인
        ↓
M1  Signature / Hash / 핵심 필드 비교
        ↓
VERIFIED 또는 TAMPERED
```

- **AI(M2)는 정보를 읽는다.** 진위 판정을 하지 않는다.
- **Blockchain(M3/M4)은 발행자와 Key의 신뢰 상태를 제공한다.** 개인정보·원문 Payload를 저장하지 않는다.
- **Backend(M1)는 증거를 조합해 최종 판정한다.**

네 명의 코드가 각각 잘 동작하는 것보다 **하나의 E2E 흐름으로 정확히 연결되는 것**이 MVP 성공 기준이다.

---

## 2. 공통 개발 원칙

1. `main`에서 직접 개발하지 않는다.
2. 공통 Scaffold는 한 번만 생성한다 (M1 Bootstrap).
3. 네 명 모두 같은 Bootstrap Commit에서 시작한다.
4. 자신의 담당 경로를 우선 수정한다.
5. 다른 담당자 소유 영역을 임의로 수정하지 않는다.
6. 공통 Schema 변경은 팀 합의 없이 진행하지 않는다.
7. 실제 개인정보를 Fixture에 넣지 않는다.
8. 실제 금융기관 로고와 상표를 사용하지 않는다.
9. API Key와 Private Key를 Git에 Commit하지 않는다.
10. 테스트하지 않은 기능을 완료했다고 기록하지 않는다.
11. AI는 진위 판정을 하지 않는다.
12. Blockchain에는 개인정보와 원문 Payload를 저장하지 않는다.
13. 작업 완료 후 PR을 생성한다.
14. 통합 Branch에는 한 번에 하나의 PR만 반영한다.
15. 통합 직후 `make mvp-test`를 다시 실행한다.

---

## 3. 역할 개요

| 역할 | 담당 | Branch | 핵심 책임 |
|----|----|----|----|
| M1 | Backend / Integration Support | `mvp/backend` | API, Verification, 공통 Core, 통합 지원 |
| M2 | AI | `mvp/ai` | LLM Adapter, Prompt, 입력 구조화 |
| M3 | Blockchain Core | `mvp/chain-core` | Registry Smart Contract |
| M4 | Blockchain Integration | `mvp/chain-integration` | Deploy, ABI, Chain Adapter, Indexer |

MVP 기간에는 Frontend를 구현하지 않는다. 시연은 Swagger UI, CLI, JSON Report, Mock 카드 결제 문자 이미지를 사용한다.
Frontend는 MVP 이후 전체 프로젝트 단계에서 다시 역할을 분리한다.

---

## 4. 공통 시작 조건 (전원 필수)

역할 작업을 시작하기 전 아래를 모두 실행하고 확인한다.

```bash
git rev-parse HEAD
uv run python scripts/ci/validate_structure.py
make env-check
make mvp-up
make seed
make db-smoke
make smoke
make env-fingerprint
```

반드시 확인할 것:

- 네 명 모두 동일한 Bootstrap Commit SHA
- 동일한 Schema / lockfile / ABI(초기 Contract Interface)
- 동일한 Docker Compose 정의
- `build/environment_fingerprint.json`의 comparable 영역 일치
  (Git SHA, Python/uv/Node/pnpm/Foundry version, Solidity compiler, lockfile hash, Schema hash, ABI hash)
- 실제 개인정보, 실제 기관 데이터, API Key가 Git에 없음

Host OS가 Windows/macOS로 다른 것은 허용된다. 공통 서비스는 Docker를 사용한다.

**환경이 다르면 기능 개발을 시작하지 않는다.**

---

## 5. Bootstrap (M1 최초 1회)

- Branch: `bootstrap/mvp-v1`
- Commit 메시지: `chore(repo): bootstrap mvp v1`
- 완료 후 Commit SHA를 팀원에게 공유 (예: `Bootstrap SHA: 5f83ab1`)
- 나머지 팀원은 개발 전 `git rev-parse HEAD`로 공유된 SHA와 일치하는지 반드시 확인한다. 다르면 개발을 시작하지 않는다.

Bootstrap 담당자 Prompt: `prompts/00_bootstrap_integrator.md`
교차 검토 Prompt: `prompts/90_cross_review.md`

---

## 6. Git Branch / Commit / PR 규칙

### Branch

```
mvp/backend
mvp/ai
mvp/chain-core
mvp/chain-integration
```

통합 Branch: `mvp/integration` (김형준님이 관리, 다른 담당자는 직접 Push하지 않음)

MVP 이후 일반 개발:

```
feature/<issue-number>-<short-name>
fix/<issue-number>-<short-name>
docs/<issue-number>-<short-name>
chore/<issue-number>-<short-name>
```

### Commit (Conventional Commits)

```
feat(api): add card notice verification endpoint
feat(analyzer): add card notice extractor
feat(contracts): add issuer registry
feat(blockchain): add chain reader
fix(api): handle missing proof
test(contracts): cover revoked issuer key
docs(api): document verification response
```

### Pull Request 제목

```
[M번호/역할] 작업 내용
```

예:

```
[M1/Backend] Verification API 구현
[M2/AI] Card Notice 필드 추출 구현
[M3/Blockchain Core] Issuer Registry 구현
[M4/Blockchain Integration] Chain Adapter 구현
```

역할 표기: `M1/Backend`, `M2/AI`, `M3/Blockchain Core`, `M4/Blockchain Integration`

MVP 기간에는 이 형식을 통일한다. 일반 개발(MVP 이후)에서는 `base: main`을 사용한다.

### PR 생성 과정

```
자기 Branch → 작업 → Test → Commit → Push → Pull Request → 교차 검토 → Integration
```

`mvp/integration`에 합칠 경우:

```
base: mvp/integration
compare: mvp/backend  (또는 mvp/ai, mvp/chain-core, mvp/chain-integration)
```

---

## 7. Agent 사용 규칙

각 담당자는 Codex 또는 Claude Code를 자신의 담당 Branch에서 실행한다.

| 역할 | Prompt |
|----|----|
| Bootstrap | `prompts/00_bootstrap_integrator.md` |
| M1 Backend | `prompts/01_mvp_backend.md` |
| M2 AI | `prompts/02_mvp_ai.md` |
| M3 Blockchain Core | `prompts/03_mvp_chain_core.md` |
| M4 Blockchain Integration | `prompts/04_mvp_chain_integration.md` |
| 교차 검토 | `prompts/90_cross_review.md` |

### Agent가 작업 전 반드시 보고해야 하는 내용

```
Loaded instruction files:
Current branch and commit:
Owned paths:
Prohibited paths:
Planned files to change:
Commands to verify:
Blocking assumptions:
```

Branch, Bootstrap SHA, 담당 경로, 금지 경로, 테스트 명령 중 하나라도 틀리면 구현을 시작하지 않는다.

### Agent가 작업 후 반드시 보고해야 하는 내용

```
Implemented:
Files changed:
Commands actually run and results:
Contract or Schema impact:
Security and privacy impact:
Handoff requests:
Remaining blockers:
```

실행하지 않은 명령/테스트를 성공했다고 기록하지 않는다.

---

## 8. Handoff 형식

다른 담당자의 수정이 필요하면 임의로 수정하지 않고 아래 형식으로 요청한다.

```
Requesting role:
Target owner:
Blocking issue:
Exact file or interface:
Current input and output:
Expected input and output:
Required test:
Deadline:
Source branch and commit:
```

예:

```
Requesting role: M1 Backend
Target owner: M2 AI
Blocking issue: Backend에서 merchant nullable 여부 확인 필요
Exact interface: CardPaymentNoticeCandidate
Current: merchant: str
Expected: merchant: str | None
Required test: missing merchant fixture
Source branch: mvp/backend
Commit: abc1234
```

---

## 9. 교차 검토

자기 PC에서 성공했다고 작업이 완료된 것이 아니다. 가능하면 다른 담당자가 해당 Branch를 받아 다시 검증한다.

| 작성자 | 검토자 | 주요 확인 |
|----|----|----|
| M1 Backend | M3 또는 M4 | Chain 결과가 API에 정확히 반영되는지 |
| M2 AI | M1 | Candidate Schema와 API(Backend) 연결 |
| M3 Blockchain Core | M4 | ABI와 배포 가능 여부 |
| M4 Blockchain Integration | M1 | BlockchainReader와 Backend 연결 |

---

## 10. MVP 통합 순서

```
1. M3 Blockchain Core
       ↓
2. M4 Blockchain Integration
       ↓
3. M2 AI
       ↓
4. M1 Backend
       ↓
5. 정상 Text 검증
       ↓
6. 정상 Image 검증
       ↓
7. 금액 변조 Image 검증
       ↓
8. Revoked / 미등록 Case
       ↓
9. Demo Smoke
```

통합 Branch: `mvp/integration` (김형준님이 관리). **한 번에 하나의 PR만 Merge**한다. 각 Merge 직후 `make mvp-test`를 실행한다.

---

## 11. MVP 필수 결과

### 정상 Case

입력:

```
Origin Mock Bank
****1234
154,000원
ORIGIN CAFE
prf_demo_001
```

결과:

```
Verification Status: VERIFIED
Lifecycle Status: ACTIVE
```

### 금액 변조 Case

실제 Proof: `154,000원`
입력: `1,540,000원`

결과:

```
Verification Status: TAMPERED
Reason: AMOUNT_MISMATCH
```

---

## 12. 전체 MVP 검증 명령

```
uv run python scripts/ci/validate_structure.py
make bootstrap-check
make mvp-up
make demo-reset
make mvp-test
make lint
make typecheck
make smoke
```

실행하지 않은 명령은 PASS로 기록하지 않는다.

---

## 13. Environment Fingerprint

비교 가능해야 하는 정보:

```
Git SHA, Python version, uv version, Node version, pnpm version,
Foundry version, Solidity compiler, lockfile hash, Schema hash, ABI hash
```

출력: `build/environment_fingerprint.json`

네 명의 `comparable` 영역이 일치해야 한다. Host OS(Windows/macOS)가 다른 것은 허용한다. 공통 서비스는 Docker를 사용한다.

---

## 14. Discord 알림

GitHub와 Discord가 연동되어 있다. 다음 활동은 Discord에서 확인한다: `Push`, `PR 생성`, `PR Close`, `PR Merge`.

PR Merge 시 커스텀 알림 예시:

```
🟢 PR MERGED
#12 [M1/Backend] Verification API 구현
작성자: GitHub ID
```

향후 CI 구성 후 `🔴 CI FAILED`, `🚀 DEPLOYED` 알림 추가 가능. Discord 알림은 개발 편의를 위한 것이며 Git 기록이나 CI 결과를 대체하지 않는다.

---

## 15. 금지 사항

MVP에서도 다음은 금지한다.

```
main 직접 Push
다른 담당자 코드를 이유 없이 수정
테스트 실패를 Disable해서 해결
Lint 또는 Type Check 비활성화
실제 개인정보 사용
실제 은행 로고 사용
API Key Commit
Private Key Commit
AI 출력만으로 VERIFIED 결정
Proof Payload 전체를 Blockchain에 저장
실행하지 않은 테스트를 PASS라고 기록
```

---

## 16. 문제 발생 시 판단 순서

```
1. 현재 사용자 요구사항
2. 루트 AGENTS.md
3. 담당 경로의 AGENTS.md
4. Schema / API 계약
5. ADR
6. 개발 실행 인스트럭션
7. 담당자 Handoff
```

다른 담당자의 영역을 임의로 수정해서 해결하지 않는다.

---

## 17. MVP 완료 체크리스트

- [ ] 네 명이 동일 Bootstrap Commit에서 시작했다.
- [ ] 구조 검사 결과가 동일하다.
- [ ] Mock Bank가 Registry에 등록된다.
- [ ] Active Key가 등록된다.
- [ ] Analyzer가 카드 알림을 구조화한다.
- [ ] AI가 진위 판정을 하지 않는다.
- [ ] Signed Proof를 조회할 수 있다.
- [ ] Signature를 검증한다.
- [ ] Payload Hash를 비교한다.
- [ ] Registry 상태를 확인한다.
- [ ] 정상 알림이 `VERIFIED + ACTIVE`다.
- [ ] 금액 변조 알림이 `TAMPERED + AMOUNT_MISMATCH`다.
- [ ] 실제 개인정보가 없다.
- [ ] Secret이 Git에 없다.
- [ ] 다른 개발환경에서 재현된다.
- [ ] `make mvp-test`가 통과한다.
- [ ] 3분 안에 시연할 수 있다.

---

## 18. 역할 요약

| 역할 | 핵심 키워드 |
|----|----|
| M1 | Backend, Verification, Common Core, Integration Support |
| M2 | AI, LLM Adapter, Prompt, Field Extraction, Fixture |
| M3 | Blockchain Core, Issuer Registry, Key Registry, Foundry Test |
| M4 | Blockchain Integration, Deploy, ABI, Chain Reader, Indexer |

---

## 19. M1 — Backend / Integration Support

### 역할

M1은 MVP의 Backend 구현과 공유 계약을 담당하고 통합을 지원한다. `mvp/integration`의 최종 병합은 김형준님(`@kimhyounjun`)이 담당한다. 최종 진위 판정은 Backend Verification Core에서 이루어진다. **AI 결과만으로 판정하지 않는다.**

전체 흐름을 최종적으로 연결한다:

```
입력 → Analyzer 결과 → Signed Proof 조회 → Blockchain Issuer/Key 조회
→ Signature 검증 → Payload Hash 비교 → 핵심 필드 비교 → Verification 결과 생성
```

### Branch

- 작업 Branch: `mvp/backend`
- 통합 Branch: `mvp/integration` (김형준님이 관리)

### 담당 경로

```
apps/api
packages/python/originproof_core
```

필요 시: `scripts/`, `tests/`, `docs/api/`

### 개발 시작 순서

1. 공유된 Bootstrap SHA 확인
2. `mvp/backend` Branch 생성
3. 루트 `AGENTS.md` 확인 → `apps/api/AGENTS.md` 확인 → `packages/python/AGENTS.md` 확인
4. 환경 검사 실행 (4장 공통 시작 조건)
5. `prompts/01_mvp_backend.md`를 Codex/Claude Code에 입력
6. Agent가 보고한 Branch/SHA/수정 경로 확인 후 구현 시작

### 주요 구현 항목

**FastAPI**
```
POST /v1/mvp/card-notices/verify
GET  /health/live
GET  /health/ready
```

**Domain**: `CardPaymentNotice`, `SignedProofEnvelope`, Verification Result, Verification Status, Lifecycle Status, Reason Code

**Proof 처리**: Proof 저장, Proof ID 조회, Issuer ID 확인, Key ID 확인, Payload 조회, Payload Hash 확인

**Verification 파이프라인**

```
Schema → Proof lookup → Issuer → Key → Signature → Payload hash
→ Lifecycle → Binding → 핵심 필드 → Replay
```

기타: Mock Analyzer 연결, Blockchain Reader 연결

### 수정하지 않는 영역

```
packages/contracts/src
packages/contracts/test
services/analyzer 내부 Prompt
services/analyzer Provider 내부 구현
```

M3 Contract 변경 필요 시 M3에게, M2 Analyzer 변경 필요 시 M2에게 Handoff (8장 형식 사용).

### Agent Prompt

`prompts/01_mvp_backend.md`

### 필수 테스트

```
make test-api
make test-integration
make mvp-test
make smoke
```

### 완료 조건

- FastAPI가 실행된다.
- Mock Analyzer 결과를 받을 수 있다.
- Proof를 조회할 수 있다.
- Blockchain Reader를 사용할 수 있다.
- Signature 검증, Hash 비교가 가능하다.
- 정상 Fixture가 `VERIFIED + ACTIVE`다.
- 금액 변조 Fixture가 `TAMPERED + AMOUNT_MISMATCH`다.
- AI 없이 Proof ID 기반 검증이 가능하다.
- 실제 실행한 테스트 결과가 PR에 기록되어 있다.

---

## 20. M2 — AI / Analyzer

### 역할

M2는 사용자가 제공한 문자 Text 또는 이미지에서 Verification에 필요한 **후보 필드를 구조화하는 역할**만 담당한다.

```
입력 → Text/Image 이해 → 필드 추출 → Pydantic Validation → Candidate 반환
```

AI는 `VERIFIED` / `TAMPERED` / `NOT_REGISTERED`를 직접 생성하지 않는다. **진위 판정은 Backend(M1)의 책임이다.**

### Branch

`mvp/ai`

### 담당 경로

```
services/analyzer
fixtures/mvp
```

### 개발 시작 순서

1. 공유된 Bootstrap SHA 확인
2. `mvp/ai` Branch 생성
3. 루트 `AGENTS.md` → `services/analyzer/AGENTS.md` → `fixtures/AGENTS.md` 확인
4. 환경 검사 실행
5. `prompts/02_mvp_ai.md`를 Codex/Claude Code에 입력
6. Agent가 담당 경로와 금지 경로를 정확히 인식했는지 확인 후 구현 시작

### 주요 구현 항목

**LLM Provider**: `LLMProvider`, `OpenAILLMProvider`, `MockLLMProvider`

공통 인터페이스: `extract_card_payment_notice(input) → CardPaymentNoticeCandidate`

**Provider 설정** (모델 이름을 코드 여러 곳에 직접 작성하지 않는다)

```
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-5.6-luna
OPENAI_REASONING_EFFORT=low
OPENAI_API_KEY=<secret>
LLM_TIMEOUT_SECONDS=20
LLM_MAX_RETRIES=2
```

**추출 필드**

```
issuer_name, masked_card, amount_minor, currency, merchant,
approved_at, proof_id, confidence, missing_fields
```

**입력 예시**

```
[Origin Mock Bank]
카드 승인
카드 ****1234
154,000원
ORIGIN CAFE
2026-09-03 12:14
Proof ID: prf_demo_001
```

**Candidate 예시**

```json
{
  "issuer_name": "Origin Mock Bank",
  "masked_card": "1234",
  "amount_minor": 154000,
  "currency": "KRW",
  "merchant": "ORIGIN CAFE",
  "approved_at": "2026-09-03T03:14:00Z",
  "proof_id": "prf_demo_001",
  "confidence": 0.98,
  "missing_fields": []
}
```

이 결과 자체가 진짜라는 의미는 아니다.

**필수 오류 처리**: refusal, timeout, rate limit, incomplete output, schema mismatch, low confidence — Provider 오류를 그대로 외부에 노출하지 않고 Domain Error로 변환한다.

### 수정하지 않는 영역

```
packages/contracts
apps/api Verification Rule
최종 Verification Status 결정 로직
```

Backend에 새로운 Candidate Field가 필요하면 M1에게 Handoff.

### Agent Prompt

`prompts/02_mvp_ai.md`

### 필수 테스트

```
make test-analyzer
make mvp-test
make smoke
```

기본 자동 테스트는 `MockLLMProvider`를 사용한다. 실제 OpenAI 호출은 기본 테스트의 필수 조건이 아니며, 개인 OpenAI API Key가 없어도 Unit/Integration Test가 깨지면 안 된다.

### 완료 조건

- Text/이미지 입력을 구조화한다.
- 정상 Fixture가 예상 Candidate와 일치한다.
- 금액 변경 Fixture가 변경된 금액을 정확히 추출한다.
- Timeout, Refusal, Schema mismatch를 처리한다.
- API Key가 Git에 없다.
- AI가 Verification Status를 생성하지 않는다.

---

## 21. M3 — Blockchain Core

### 역할

M3는 OriginProof에서 신뢰 상태를 저장하는 Smart Contract를 담당한다. 최소한 다음을 구현한다:

```
IssuerRegistry
IssuerKeyRegistry
```

Blockchain은 전체 Proof Payload를 저장하는 DB가 아니다. Blockchain의 역할은 **Shared Trust State**다.

### Branch

`mvp/chain-core`

### 담당 경로

```
packages/contracts/src
packages/contracts/test
```

### 개발 시작 순서

1. 공유된 Bootstrap SHA 확인
2. `mvp/chain-core` Branch 생성
3. 루트 `AGENTS.md` → `packages/contracts/AGENTS.md` 확인
4. 환경 검사 실행
5. `prompts/03_mvp_chain_core.md`를 Codex/Claude Code에 입력
6. Agent가 Contract Core 외 영역을 수정하지 않는지 확인 후 구현 시작

### 주요 구현 항목

**Issuer Registry** — 최소 상태: `ACTIVE`, `SUSPENDED`
- Issuer 등록 / 상태 조회 / 중복 등록 방지 / 관리자 권한 / 상태 변경 / Event

**Issuer Key Registry**
- Key 등록 / 조회 / 유효 기간 / 폐기 / 회전 / Revoked 상태

### 필수 보안 테스트

```
정상 등록
권한 없는 등록
중복 등록
zero address
Key revoke
중복 revoke
상태 조회
Event 발생
```

가능하면 Foundry fuzz test를 사용한다.

### Blockchain에 저장하지 않는 데이터

```
카드 결제 문자, OCR 결과, 사용자 입력 원문, 개인정보,
전체 Proof Payload, API Key, Private Key
```

### 수정하지 않는 영역

```
apps/api
services/analyzer
packages/contracts 최종 deployment 산출물
```

Deploy와 Backend 연결은 M4가 담당한다. Contract Interface가 바뀌면 M4에게 반드시 Handoff한다.

**Handoff 예시 (M3 → M4)**

```
Requesting role: M3
Target owner: M4
Blocking issue: IssuerKeyRegistry interface changed
Exact interface: getKeyStatus(bytes32 issuerId, bytes32 keyId)
Current output: bool
Expected output: KeyStatus enum
Required test: Python BlockchainReader must return ACTIVE / REVOKED
Source branch: mvp/chain-core
Commit: <commit SHA>
```

### Agent Prompt

`prompts/03_mvp_chain_core.md`

### 필수 테스트

```
make test-contracts
make mvp-test
```

### 완료 조건

- Issuer 등록/상태 조회 가능
- Key 등록/상태 조회/revoke 가능
- Unauthorized 접근 차단, 중복 등록 차단
- Event 발생
- Foundry Test 통과
- 개인정보가 Chain에 없음

---

## 22. M4 — Blockchain Integration

### 역할

M4는 M3가 구현한 Smart Contract를 실제 Backend에서 사용할 수 있도록 연결한다.

```
M3 Smart Contract 구현 → M4 배포+ABI+Python 연결 → M1 Verification Engine 사용
```

### Branch

`mvp/chain-integration`

### 담당 경로

```
services/indexer
packages/contracts/script
packages/contracts/deployments
packages/contracts/abi
apps/api/src/infrastructure/blockchain
local chain 관련 infra
```

### 개발 시작 순서

1. 공유된 Bootstrap SHA 확인
2. `mvp/chain-integration` Branch 생성
3. 루트 `AGENTS.md` → `services/indexer/AGENTS.md` → `packages/contracts/AGENTS.md` 확인
4. 환경 검사 실행
5. `prompts/04_mvp_chain_integration.md`를 Codex/Claude Code에 입력
6. M3 Contract Interface 상태 확인 후 Deploy/Adapter 구현 시작

### 주요 구현 항목

- **Local Chain**: 로컬 EVM 실행, Contract 배포, Mock Bank 등록, Mock Bank Key 등록
- **Deployment Manifest** 기록: chain ID, contract address, commit SHA, constructor arguments
- **ABI**: M3 Contract에서 생성 (임의로 손으로 작성하지 않음)
- **Blockchain Reader**: 예) `get_issuer_status()`, `get_key_status()` — Backend가 Contract 내부 구조를 직접 알지 않아도 되도록 한다
- **Indexer**: `block number + log index` 조합으로 Event 중복 처리 방지, 재시작해도 동일 Event 중복 반영 금지

### 중요 규칙

ABI를 직접 손으로 작성하지 않는다 (M3 Contract에서 생성). M3 Interface가 확정되지 않았다면 임의의 가짜 Contract Interface를 만들지 않고, 필요하면 명시적인 Mock Port를 사용한다.

### 수정하지 않는 영역

```
packages/contracts/src
packages/contracts/test
services/analyzer
공통 Pydantic Schema
```

Contract Core 수정이 필요하면 M3에게 Handoff한다.

### Agent Prompt

`prompts/04_mvp_chain_integration.md`

### 필수 테스트

```
make test-integration
make mvp-test
make smoke
```

### 완료 조건

- Local Chain 실행, Contract 배포
- Mock Bank 등록, Key 등록
- ABI 생성, Deployment Manifest 생성
- Python에서 Issuer/Key/Revoked 상태 조회 가능
- 재시작과 중복 Event 처리 가능
- Backend에서 Blockchain Reader 사용 가능

---

## 23. 최종 원칙

OriginProof MVP의 목표는 많은 기능을 만드는 것이 아니다. 하나의 흐름을 네 명이 서로 다른 담당 영역에서 구현하고 마지막에 정확하게 연결하는 것이 목표다.

**AI는 정보를 읽는다.**
**Blockchain은 발행자와 Key의 신뢰 상태를 제공한다.**
**Backend는 증거를 조합해 최종 판정한다.**
