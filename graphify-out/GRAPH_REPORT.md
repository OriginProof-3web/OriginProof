# Graph Report - OriginProof-agent-plan  (2026-09-30)

## Corpus Check
- 150 files · ~51,641 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 24 file(s) not represented in the graph (top: (none) 8, .sol 6, .Dockerfile 4)

## Summary
- 1346 nodes · 2298 edges · 135 communities (126 shown, 9 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 178 edges (avg confidence: 0.93)
- Token cost: not measured (agent-session semantic extraction)

## Community Hubs (Navigation)
- Deterministic Verification
- API Request Lifecycle
- Blockchain RPC Reader
- Verification Result Schema
- Analyzer Input Pipeline
- Shared Core Imports
- Card Notice Schema
- Finals Cryptographic Contracts
- Finals Development Plan
- Database Event Projection
- Analyzer Provider Wiring
- Historical Chain Handoffs
- Analyzer Failure Handling
- Agent Ownership Rules
- Web Component Testing
- TypeScript Compiler Configuration
- W3 Issuance Integration
- Analyzer Evaluation Inputs
- Serena Memory Navigation
- Web Demo Rendering
- W7 Release Rehearsal
- Historical Analyzer Handoff
- Web Development Dependencies
- Analyzer Service Interface
- W5 Role Integration
- W4 Lifecycle Consume
- W6 Recovery Verification
- Product Scope Overview
- W1 Authentication Contracts
- W2 Institution Operations
- Candidate Verification Boundaries
- Generated TypeScript Contracts
- Backend Web Boundaries
- Web Ownership Accessibility
- API Ownership Authorization
- Proof Enum Definitions
- Proof Envelope Properties
- Web Package Scripts
- Local Container Services
- Historical Extraction Handoff
- Environment Fingerprint Comparison
- Current Versus Archived Prompts
- Analyzer Quality Guidance
- Card Extraction Prompt
- Candidate Provider Interface
- Indexer Recovery Rules
- Contribution Verification Evidence
- Blockchain Ownership Operations
- Runtime Configuration Sources
- Next Application Layout
- ESLint Configuration
- Workspace Package Metadata
- Generated Contract Ownership
- Candidate Schema Definition
- Request Schema Definition
- Request Candidate Properties
- Candidate Domain Definition
- Finals Task Prompt
- Analyzer Test Fixtures
- CI Quality Gates
- Analyzer Ownership Memory
- Portfolio Contribution Records
- Historical Reader Interface
- MVP Demo Commands
- Missing Field Schema
- Envelope Schema Definition
- Missing Field Items
- Proof Identifier Schema
- Historical Contract Prompt
- Cross Review Procedure
- Environment Prerequisite Regression
- Historical Reader Handoff
- Historical Bootstrap Procedure
- Contract Ownership Policy
- Candidate Confidence Bounds
- Application Domain Bounds
- Card Domain Definition
- Masked Card Format
- Issuer Name Bounds
- Merchant Name Bounds
- Nonce Field Bounds
- Transaction Identifier Bounds
- Confidence Range Schema
- Historical Backend Prompt
- Historical Analyzer Prompt
- Historical Integration Prompt
- Schema Generation Pipeline
- Development Entry Instructions
- Serena Workspace Configuration
- Browser Accessibility Tests
- Web Runtime Dependencies
- Historical Integration Sequence
- Synthetic Fixture Ownership
- amount minor Schema
- approved at Schema
- currency Schema
- issuer name Schema
- masked card Schema
- merchant Schema
- proof id Schema
- transaction id Schema
- amount minor Schema
- approved at Schema
- chain id Schema
- currency Schema
- expires at Schema
- issued at Schema
- issuer id Schema
- key id Schema
- metadata hash Schema
- payload hash Schema
- proof id Schema
- schema version Schema
- signature Schema
- single use Schema
- subject binding hash Schema
- amount minor Schema
- approved at Schema
- currency Schema
- issuer name Schema
- masked card Schema
- merchant Schema
- transaction id Schema
- Node Workspace Build Policy
- Merge Notification Workflow
- Documentation Ownership Policy
- Historical Candidate Contract
- Analyzer Input Validation
- Foundry Dependency Remappings
- Python Workspace Packages
- API Package Entry
- Next Generated Types
- Service Smoke Script
- Analyzer Package Entry
- Workspace Package Identity

## God Nodes (most connected - your core abstractions)
1. `OriginProof 통합 개발 계획서` - 137 edges
2. `SemanticInput` - 42 edges
3. `AnalyzerError` - 35 edges
4. `VerificationService` - 34 edges
5. `JsonRpcBlockchainReader` - 28 edges
6. `MockLLMProvider` - 22 edges
7. `SemanticInterface` - 22 edges
8. `ADR 0001 — 본선 두 유형·상태·키·수신자·체인 처리` - 21 edges
9. `DependencyUnavailableError` - 20 edges
10. `create_app()` - 20 edges

## Surprising Connections (you probably didn't know these)
- `Verification SHA, environment, command and outcome` --semantically_similar_to--> `Actual SHA, environment, results and limitations`  [INFERRED] [semantically similar]
  .github/pull_request_template.md → .serena/memories/task_completion.md
- `AI candidate extraction only` --semantically_similar_to--> `AI only extracts candidate fields`  [INFERRED] [semantically similar]
  .serena/memories/analyzer/core.md → AGENTS.md
- `Verification status and lifecycle separation` --semantically_similar_to--> `Lifecycle-aware usability display`  [INFERRED] [semantically similar]
  .serena/memories/backend/core.md → apps/web/AGENTS.md
- `Persist Operation before external changes` --semantically_similar_to--> `Replay, duplicate and restart safe event projection`  [INFERRED] [semantically similar]
  apps/api/AGENTS.md → .serena/memories/blockchain/core.md
- `DB·서명기·manifest·chain 배포 일치` --semantically_similar_to--> `deployment_id와 배포 block/hash`  [INFERRED] [semantically similar]
  infra/AGENTS.md → docs/adr/0001-finals-contracts.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Finals A-D ownership** — agents_role_a, agents_role_b, agents_role_c, agents_role_d [EXTRACTED 1.00]
- **서버 인증·불변 commitment·수신자 binding·체인 단일 사용** — docs_adr_0001_finals_contracts_trusted_gateway, docs_adr_0001_finals_contracts_immutable_commitment, docs_adr_0001_finals_contracts_recipient_binding, docs_adr_0001_finals_contracts_atomic_consume [EXTRACTED 1.00]
- **A/B/C/D 본선 역할별 공동 개발** — docs_development_plan_role_a, docs_development_plan_role_b, docs_development_plan_role_c, docs_development_plan_role_d [EXTRACTED 1.00]
- **P0 three-role web service** — readme_user_screen, readme_issuer_console, readme_operator_screen [EXTRACTED 1.00]
- **Candidate-only extraction trust boundary** — services_analyzer_agents_candidate_only, services_analyzer_src_originproof_analyzer_prompts_card_payment_notice_v3_untrusted_input, services_analyzer_readme_strict_json, services_analyzer_readme_safe_logging [INFERRED 0.95]

## Communities (135 total, 9 thin omitted)

### Community 0 - "Deterministic Verification"
Cohesion: 0.05
Nodes (65): enum, field_validator, canonical_json_bytes(), _normalize(), payload_hash(), Any, datetime, Return canonical UTF-8 JSON shared by Python and Solidity Golden Fixtures. (+57 more)

### Community 1 - "API Request Lifecycle"
Cohesion: 0.06
Nodes (39): Database, configured_blockchain_reader(), create_app(), invalid_request(), datetime, FastAPI, _request_id(), UnavailableBlockchainReader (+31 more)

### Community 2 - "Blockchain RPC Reader"
Cohesion: 0.08
Nodes (35): address(), digest(), JsonRpcBlockchainReader, datetime, M1 port adapter. All registry calls within one operation use the same block., uint(), crypto_hash, infrastructure_blockchain_reader (+27 more)

### Community 3 - "Verification Result Schema"
Cohesion: 0.04
Nodes (46): additionalProperties, type, additionalProperties, title, type, $defs, LifecycleStatus, ReasonCode (+38 more)

### Community 4 - "Analyzer Input Pipeline"
Cohesion: 0.09
Nodes (33): fastapi_testclient, logging, run_case(), BaseModel, Untrusted input transport model, not an alternative domain Candidate schema., SemanticInput, create_app(), capabilities() (+25 more)

### Community 5 - "Shared Core Imports"
Cohesion: 0.11
Nodes (22): Base, SignedProofRow, asyncio, datetime, DeclarativeBase, eth_keys, eth_keys_exceptions, httpx (+14 more)

### Community 6 - "Card Notice Schema"
Cohesion: 0.05
Nodes (37): additionalProperties, exclusiveMinimum, title, type, format, title, type, pattern (+29 more)

### Community 7 - "Finals Cryptographic Contracts"
Cohesion: 0.07
Nodes (34): ProofStatusRegistry 원자적 consume, PROOF_ONLY / FULL_COMPARISON / PARTIAL_COMPARISON, 유출 키 폐기·과거 Proof 사용 차단, deployment_id와 배포 block/hash, ADR 0001 — 본선 두 유형·상태·키·수신자·체인 처리, schema 2.0.0 / originproof.finals, 불변 Proof commitment, PROOF_REVOKED → ISSUER_KEY_REVOKED → ISSUER_SUSPENDED → CONSUMED → EXPIRED → ACTIVE (+26 more)

### Community 8 - "Finals Development Plan"
Cohesion: 0.06
Nodes (33): AI 후보 필드 추출, OriginProof 통합 개발 계획서, F01 신규 요청형·문서형 Proof 발행 후 검증, F02 같은 ID의 금액 또는 문서번호 변경, F03 만료된 Proof, F04 1회성 Proof의 순차·동시 consume, F05 기관 A가 기관 B의 키·Proof 변경, F06 등록되지 않은 Proof·발행자 조회 (+25 more)

### Community 9 - "Database Event Projection"
Cohesion: 0.09
Nodes (15): alembic, do_run_migrations(), run_migrations_online(), dataclasses, logging_config, ChainEvent, ProjectionStore, SQLAlchemy event projection; chain state remains authoritative. (+7 more)

### Community 10 - "Analyzer Provider Wiring"
Cohesion: 0.13
Nodes (17): collections_abc, importlib_resources, OpenAI, pydantic, pydantic_settings, re, AnalyzerErrorCode, StrEnum (+9 more)

### Community 11 - "Historical Chain Handoffs"
Cohesion: 0.08
Nodes (28): 입력 Candidate 비저장, MVP card-notice verification API, INCONCLUSIVE + DEPENDENCY_UNAVAILABLE, signed_proofs 신뢰 원본 저장, VerificationResult, POST /v1/mvp/card-notices/verify, M3 — 스마트 계약 코어, 2026-09-07 계약 10개·fuzz 512회 검증 기록 (+20 more)

### Community 12 - "Analyzer Failure Handling"
Cohesion: 0.19
Nodes (19): Exception, AnalyzerError, Only fixed, safe messages cross the provider boundary., make_provider(), fixture, parametrize, The real OpenAI SDK over MockTransport: no API key, external request, or live…, response_body() (+11 more)

### Community 13 - "Agent Ownership Rules"
Cohesion: 0.10
Nodes (17): Author tests and independent QA remain distinct, GitHub workflow ownership and least privilege, ADR 0001 approved finals contracts, Work branch → phase/Wn → integration, On-chain atomic single-use authority, Independent implementation, connection pending, integration verified, phase complete, Finals W1-W7 development plan v3.0, Separate Registry operator and issuer signing keys (+9 more)

### Community 14 - "Web Component Testing"
Cohesion: 0.12
Nodes (15): name, private, version, eslint, eslint-config-next, jsdom, react, react-dom (+7 more)

### Community 15 - "TypeScript Compiler Configuration"
Cohesion: 0.11
Nodes (17): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+9 more)

### Community 16 - "W3 Issuance Integration"
Cohesion: 0.27
Nodes (17): W1-C3 ADR 0001의 두 유형·필드·domain/version·binding·single_use와 검증/lifecycle/reason·검사 순서·NOT_RUN을 Python 모델로 구현합니다. B와 서명/체인 경계를 검토하고 Schema·타입·Golden Fixture를 생성합니다., W3 개발 단계, W3-A1 승인된 두 유형의 필수 필드·기간·수신자 입력 폼과 제출/실패/재시도 상태를 구현합니다. 서버의 필드 오류를 해당 입력에 연결합니다., W3-A2 자기 기관 Proof 목록/상세·ID 복사·QR/검증 링크를 구현합니다. 링크에는 원문·개인키·인증 토큰을 넣지 않습니다., W3-A3 로그인 없는 ID 조회와 받은 자료의 필드 비교를 별도 동작으로 연결합니다. 검사 범위·생명주기·실패/미실행 검사를 표시합니다., W3-B1 발행/검증이 사용하는 기관·키 상태와 기간 조회를 확인하고 RPC 오류·미등록·network 불일치를 Adapter 계약에 맞게 반환합니다., W3-B2 C의 새 유형 Golden Fixture를 해시·서명·domain 관점에서 교차 검증하고 다른 chain ID·schema version·proof type의 재사용 실패를 확인합니다., W3-B3 ProofStatusRegistry의 조회·폐기·consume·이벤트 ABI와 호출자/Proof 소유자/수신자 권한 연결을 문서화합니다. C와 상태 조회 및 오류 예시를 확정합니다. (+9 more)

### Community 17 - "Analyzer Evaluation Inputs"
Cohesion: 0.19
Nodes (13): argparse, base64, io, pil, evaluate(), main(), Path, Deterministic synthetic-fixture evaluation; deliberately no live-provider… (+5 more)

### Community 18 - "Serena Memory Navigation"
Cohesion: 0.13
Nodes (11): Work branch to phase/Wn to integration, Shared model generated consumer contracts, No secrets, personal data or complete payload on-chain or in logs, Apps and services depend on packages, OriginProof, Finals P0 synthetic institutions and two proof types, Stable non-obvious conventions only, Progressive memory discovery (+3 more)

### Community 19 - "Web Demo Rendering"
Cohesion: 0.16
Nodes (11): ApiError, asUtc(), baselineProof, checkValue(), DemoPage(), flowSteps, FormState, normalPreset (+3 more)

### Community 20 - "W7 Release Rehearsal"
Cohesion: 0.33
Nodes (15): W6-A3 두 기관의 실제 발행·검증·폐기·사용 장면과 근거를 중심으로 발표 초안을 만들고 미구현 기능 표현을 제거합니다., W6-D3 A/B/C와 출시 차단 결함·잔여 위험·후보 SHA를 확인하고 기능 동결 체크를 정리합니다., W7 개발 단계, W7-A1 W6에서 확인한 시연 차단 UI·접근성·표현 오류를 좁은 PR로 수정하고 관련 화면 검사를 다시 실행합니다., W7-A2 실제 후보 버전으로 발표 자료·전체 시연 영상·장애 시 영상 전환 대본을 완성합니다., W7-A3 로컬 기기/브라우저·화면 순서·역할별 세션·발표 담당자 동선을 리허설에 맞추고 제출 자료를 목록화합니다., W7-B1 동결 후 남은 Contract/Adapter/indexer 결함을 수정하고 ABI·배포 변경 영향을 재검증합니다., W7-B2 후보 SHA의 계약·ABI·네트워크·주소·배포 인자·signer 공개정보를 대조하고 배포 목록을 확정합니다. (+7 more)

### Community 21 - "Historical Analyzer Handoff"
Cohesion: 0.14
Nodes (13): Archived MVP M2 to M1 implementation handoff, Historical 10-field CardPaymentNoticeCandidate with transaction_id, Historical Docker/Foundry and smoke verification gaps, Historical bytecode contamination of schema tree fingerprint, Historical model default gpt-5.6-luna, Historical OpenAI SDK 2.54.0 and Pillow 12.3.0 integration request, Historical 97 analyzer and 111 Python tests passed, Superseded historical bootstrap audit at 4ee98f3 (+5 more)

### Community 22 - "Web Development Dependencies"
Cohesion: 0.14
Nodes (14): devDependencies, @axe-core/playwright, eslint, eslint-config-next, @eslint/eslintrc, jsdom, @playwright/test, @testing-library/jest-dom (+6 more)

### Community 23 - "Analyzer Service Interface"
Cohesion: 0.22
Nodes (13): OriginProof Analyzer card-notice extraction, CardPaymentNoticeCandidate ten-field response, POST /v1/analyze/card-payment-notice, 422 input/refusal/confidence; 502 schema/incomplete; 503 availability/rate limit; 504 timeout, Text 1–10000 chars; PNG/JPEG/WebP max 5 MiB, single frame, 12 MP, No silent mock fallback after OpenAI failure, OpenAI Responses provider with Pydantic Structured Outputs, SDK-only retry loop: two retries, per-request 20-second timeout (+5 more)

### Community 24 - "W5 Role Integration"
Cohesion: 0.26
Nodes (13): W1-D1 기존 정상/금액 변조 MVP 재현을 독립 확인하고 F01~F15를 역할·입력·기대 상태·검증 계층별 사례표로 나눕니다. 기존 검사로 덮이지 않는 항목을 기록합니다., W5 개발 단계, W5-A1 세 역할 화면의 빈 결과·잘못된 입력·세션 만료·요청 대기·오류·재시도 이동을 정리합니다., W5-A2 키보드 탐색·focus·레이블·오류 읽기·대비·작은 화면을 점검하고 필요한 UI를 수정합니다., W5-B1 이벤트 중복·처리 순서·checkpoint 갱신을 점검하고 재시작 시 누락/중복 상태가 없도록 구현을 보완합니다., W5-B2 reorg/미확정 블록 처리와 현재 체인 재조회 규칙을 구현·정리합니다. rewind 시 실제 공통 조상을 확인합니다., W5-B3 Registry·Adapter·manifest·쓰기 역할의 일치와 운영키/발행키 분리를 점검하고 배포 자료를 갱신합니다., W5-C1 변경 API 전수 목록에 인증·기관 소속·객체 소유·입력 제한·요청 제한·idempotency를 대조해 누락을 수정합니다. (+5 more)

### Community 25 - "W4 Lifecycle Consume"
Cohesion: 0.36
Nodes (11): W4 개발 단계, W4-A1 새 키 준비·등록 확인·발행 전환·이전 키 처리 순서를 보여주는 교체 화면을 연결합니다. 정상 교체와 유출 폐기를 구분합니다., W4-A3 지정 수신자 테스트 계정의 로그인과 consume 동작을 연결하고, 이미 사용됨·권한 없음·대기·실패를 처리합니다. 일반 조회와 버튼을 분리합니다., W4-B1 승인 ABI로 Proof 폐기·상태 조회·이벤트를 구현하고 발행자와 Proof의 연결 및 호출 권한을 검증합니다., W4-B2 소비 가능 상태·기간·수신자/발행자 권한·서명 근거를 검사하고 원자적으로 consume 상태를 전이합니다., W4-B3 새 ABI·배포 manifest·상태 Reader/Writer·이벤트 projection을 연결하고 receipt 이후 재조회를 제공합니다., W4-C1 새 서명기 생성·키 등록 확인·발행 키 선택 변경·이전 키 상태 처리를 연결합니다. 교체 중 실패 시 발행 키 상태를 일관되게 유지합니다., W4-C3 인증 계정과 서명된 수신자 binding을 대조한 뒤 consume을 호출합니다. 요청 ID·Operation으로 재시도/동시 요청을 추적하고 조회 API를 읽기 전용으로 유지합니다. (+3 more)

### Community 26 - "W6 Recovery Verification"
Cohesion: 0.36
Nodes (11): W5-C3 로컬 Compose 설정·기동 준비 상태·테스트 계정 준비·DB migration·seed를 정리합니다. 이미 존재하는 명령을 재사용합니다., W6 개발 단계, W6-A1 실제 API timeout·RPC 보류·세션 만료·실패 receipt에서 화면 안내와 재시도 후 이동을 확인하고 수정합니다., W6-A2 로컬 브라우저의 시연 동선·화면 배율·새 세션 전환·네트워크 표기를 정리합니다. QR을 다른 기기에서 쓸 경우 선택된 LAN 구성을 검증합니다., W6-B1 RPC 단절/복구·receipt 지연·실패·중복 이벤트·reorg를 재현해 Contract/Adapter/indexer 동작을 검증합니다., W6-B2 로컬 체인 재기동/재배포 후 manifest·주소·chain ID·이벤트 시작점과 seed signer를 맞추는 복구 절차를 검증합니다. 테스트넷 연결은 이번 복구 완료의 조건이 아닙니다., W6-C1 발행·등록·consume의 동시 요청과 DB/체인 사이 프로세스 종료·재시작을 재현하고 복구 경로를 보완합니다., W6-C2 세션 만료/로그아웃·CSRF·권한 우회·키 파일 접근·로그/응답 비밀정보·요청 제한을 검사하고 발견 사항을 수정합니다. (+3 more)

### Community 27 - "Product Scope Overview"
Cohesion: 0.27
Nodes (10): Browser to API, database and chain to refreshed state acceptance, Local demo bootstrap, seed, chain deployment and HTTP checks, Existing card-notice MVP and web demo, W1-W7 development stages, not fixed calendar weeks, Issuer onboarding, keys, issue and revoke console, OFFICIAL_DOCUMENT, Operator approval, rejection, suspension and audit, OriginProof issuer, integrity and current validity verification (+2 more)

### Community 28 - "W1 Authentication Contracts"
Cohesion: 0.44
Nodes (10): W1 개발 단계, W1-A1 사용자·기관·운영자의 화면 흐름, 역할별 허용 동작, 입력·대기·오류 화면을 정의합니다. Proof ID 조회와 내용 비교의 결과 표현을 구분합니다., W1-A2 기존 Next.js 앱에 로그인·로그아웃·현재 사용자 표시와 역할별 이동을 연결합니다. 세션 만료·권한 거부·재로그인 화면을 처리합니다., W1-A3 기관 신청 생성·자기 신청 조회, 운영자 신청 조회·검토 결정 화면을 연결합니다. 결정 저장과 체인 활성화 상태를 따로 표시합니다., W1-B1 기존 Issuer/Key Registry·Reader·배포를 조사하고 기관 활성화·중지, 키 등록·폐기 호출과 쓰기 권한을 정의합니다. B/C 사이 입력·반환·오류·확정 기준·조회 방법을 문서화합니다., W1-B2 ADR 0001의 발행키/운영키 분리, 정상 교체·유출 폐기·기존 Proof, gateway·consume 정책을 Contract/Adapter 설계에 반영합니다. 확정된 receipt·재기동/재배포 기준을 구현 명세로 작성합니다., W1-C1 A와 로그인·로그아웃·현재 계정/기관 API, 인증 실패·권한 실패·작업 대기 응답을 정의합니다. ADR 0001의 테스트 계정 공급·8시간 세션·CSRF·쿠키/자격증명 보호 조건을 모델/API에 반영합니다. 회원가입·외부 인증은 추가하지 않습니다., W1-C2 인증·세션, 계정/기관 소속 저장, 공통 서버 권한 검사를 구현합니다. 합성 운영자·서로 다른 두 기관 담당자·수신자 계정 준비 방법을 추가합니다. (+2 more)

### Community 29 - "W2 Institution Operations"
Cohesion: 0.49
Nodes (10): W2 개발 단계, W2-A1 기관 신청/검토 화면에 승인·반려·중지·사유·이력을 연결합니다. 제출/확인 대기·성공·실패·재시도와 현재 네트워크를 표시합니다., W2-A2 자기 기관의 키 생성·등록·목록·상세·폐기 화면과 작업 상태 조회를 연결합니다. 승인 전·만료·폐기 키의 동작 제한을 표시합니다., W2-B1 W1 승인 ABI에 따라 기관 활성화·중지와 키 등록·조회·폐기 권한을 구현/재사용합니다. Adapter 쓰기·읽기·오류 매핑, ABI와 배포 manifest를 함께 맞춥니다., W2-B2 로컬 EVM에 배포하고 제출 hash와 확정 receipt·상태 재조회를 연결합니다. indexer의 중복 이벤트·checkpoint 재시작 처리를 연결합니다., W2-C1 Operation/AuditEvent 저장·상태 조회·기관별 접근 제한을 구현합니다. 요청 ID의 주체/동작 범위와 입력 일치 여부를 검사하고, 재시도 시 기존 작업을 조회합니다. DB와 체인 사이 부분 실패를 추적합니다., W2-C2 신청 승인·반려·기관 중지 API를 B의 Adapter와 연결합니다. 운영자 권한·자체 승인 금지·타 기관 접근을 서버에서 검사하고 확인된 활성 상태만 키 관리에 사용합니다., W2-C3 기관별 보호된 합성 서명기 생성·보관과 공개키 관리 API를 구현합니다. challenge 서명으로 signer 대응을 확인한 뒤 B의 키 등록/폐기를 호출합니다. (+2 more)

### Community 30 - "Candidate Verification Boundaries"
Cohesion: 0.20
Nodes (8): NFC, sorted JSON, UTC and integer minor currency units, B reviews chain and signature compatibility before completion, External queries injected through ports, Separate signature, content scope, current usability and unexecuted checks, Preserve card v1; ADR policies for finals types and new versions, Extract candidates without authenticity or Registry decisions, card_payment_notice_v3 bundled prompt, Extract only visible card-payment candidate fields

### Community 31 - "Generated TypeScript Contracts"
Cohesion: 0.20
Nodes (9): CardPaymentNotice, CardPaymentNoticeCandidate, LifecycleStatus, ProofType, ReasonCode, SignatureScheme, SignedProofEnvelope, VerificationResult (+1 more)

### Community 32 - "Backend Web Boundaries"
Cohesion: 0.22
Nodes (7): Verification status and lifecycle separation, Request and task scoped database sessions, Pure shared Pydantic verification core, Generated TypeScript types and API boundary, Verification, lifecycle and usability semantics, Loading, empty, partial, error and permission denial, Lifecycle-aware usability display

### Community 33 - "Web Ownership Accessibility"
Cohesion: 0.22
Nodes (7): Role A: web, UX and accessibility, Playwright, keyboard, responsive and actual API validation, Approved generated API types, Read-only lookup distinct from consume, Public Proof ID only in QR and links, User, issuer and operator web UX, Web AGENTS entrypoint

### Community 34 - "API Ownership Authorization"
Cohesion: 0.22
Nodes (7): Role C: API, shared Python core and integration, Authentication, authorization, issuance, verification, Operation and AuditEvent, Do not report DB or mock success as chain completion, Real PostgreSQL and adapter integration tests, Server-side ownership, CSRF and recipient checks, Separate AsyncSession per request or task, API AGENTS entrypoint

### Community 35 - "Proof Enum Definitions"
Cohesion: 0.22
Nodes (9): $defs, ProofType, SignatureScheme, enum, title, type, enum, title (+1 more)

### Community 36 - "Proof Envelope Properties"
Cohesion: 0.22
Nodes (9): $ref, default, $ref, properties, payload, proof_type, signature_scheme, default (+1 more)

### Community 37 - "Web Package Scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, start, test, test:e2e, typecheck

### Community 38 - "Local Container Services"
Cohesion: 0.43
Nodes (7): Analyzer container on port 8001, Anvil local EVM chain 31337, API container on port 8000, Foundry deployer container, PostgreSQL 16.4 with persistent data volume, Redis 7.4.1 without persistence, Web container on loopback port 3000

### Community 39 - "Historical Extraction Handoff"
Cohesion: 0.29
Nodes (8): CardPaymentNoticeCandidate, M2 실행 문서 카드 알림 후보 추출, 과거 MVP 후보 추출 작업 범위, LLMProvider, null·missing_fields·confidence, MockLLMProvider, OpenAILLMProvider, Responses API·Pydantic Structured Outputs

### Community 40 - "Environment Fingerprint Comparison"
Cohesion: 0.39
Nodes (7): hashlib, platform, command(), digest(), main(), Path, tree_digest()

### Community 41 - "Current Versus Archived Prompts"
Cohesion: 0.25
Nodes (6): Archived MVP bootstrap instructions, Historical CARD_PAYMENT_NOTICE, Candidate, SignedProofEnvelope and status contracts, Historical reproducible Compose: FastAPI, Analyzer, PostgreSQL, Redis, local EVM, Historical synthetic normal and amount-tampered fixtures, Bootstrap and MVP prompts preserved for audit only, Current finals task and cross-review prompts

### Community 42 - "Analyzer Quality Guidance"
Cohesion: 0.25
Nodes (6): Mock default provider and gpt-6-luna default model, Paid live API tests require explicit opt-in; replay is not extraction accuracy, D owns candidate extraction, providers, prompts and synthetic evaluation, Finals P0 works without AI; OCR, image and PDF extensions are P1, Eight synthetic texts and two image replays; no live model or calibrated confidence, MockLLMProvider template parser and injected hash transcript replay

### Community 43 - "Card Extraction Prompt"
Cohesion: 0.25
Nodes (7): UTC approval timestamp; template-specific KST for timezone-free Korean notices, KRW integer won; explicit uppercase three-letter currency, Extraction confidence is not authenticity or calibrated probability, Never infer transaction_id from proof_id, Return final four visible card digits only, Timezone-aware ISO 8601 with synthetic-template KST exception, Artifact instructions are untrusted data

### Community 44 - "Candidate Provider Interface"
Cohesion: 0.29
Nodes (4): LLMProvider, _parse_mock_text(), CardPaymentNoticeCandidate, Protocol

### Community 45 - "Indexer Recovery Rules"
Cohesion: 0.25
Nodes (6): Only unregistered is absent; RPC, ABI and network failures are dependency errors, Chain ID, address, deployment SHA, args and deployment identity, Block/log identity and checkpoint support duplicate and restart handling, B owns projection, checkpoints, deployment, manifest and blockchain adapter, Projection is not authoritative current chain state, Do not mix old projection or Proof with redeployed environment

### Community 46 - "Contribution Verification Evidence"
Cohesion: 0.29
Nodes (5): Individual contribution and AI usage evidence, Phase completion PR evidence, Verification SHA, environment, command and outcome, Actual SHA, environment, results and limitations, Independent review and clean reproduction

### Community 47 - "Blockchain Ownership Operations"
Cohesion: 0.29
Nodes (6): Registry final authority and atomic consume, Deployment chain ID, address, source SHA and arguments, Replay, duplicate and restart safe event projection, Registry operator and issuer key separation, Role B: contracts, indexer and blockchain adapter, Persist Operation before external changes

### Community 48 - "Runtime Configuration Sources"
Cohesion: 0.29
Nodes (6): Solidity, Foundry and OpenZeppelin, Container-based Foundry checks, OpenAI Responses API through LLMProvider, Python, uv, FastAPI and Pydantic, SQLAlchemy, Alembic, PostgreSQL, Redis and Celery, Next.js and TypeScript

### Community 49 - "Next Application Layout"
Cohesion: 0.29
Nodes (4): metadata, apps_web_app_styles, nextConfig, next

### Community 50 - "ESLint Configuration"
Cohesion: 0.29
Nodes (6): baseDirectory, compat, config, @eslint/eslintrc, ref_node_path, ref_node_url

### Community 51 - "Workspace Package Metadata"
Cohesion: 0.29
Nodes (6): name, packageManager, private, scripts, lint, typecheck

### Community 52 - "Generated Contract Ownership"
Cohesion: 0.29
Nodes (5): C-owned Pydantic domain models and deterministic verification, C-owned JSON Schema and TypeScript generation, Version transitions tied to ADR and migration policies, Regeneration must produce no diff and consumers must compile, Generate from Pydantic models or Contract events

### Community 53 - "Candidate Schema Definition"
Cohesion: 0.29
Nodes (6): additionalProperties, description, required, $schema, title, type

### Community 54 - "Request Schema Definition"
Cohesion: 0.29
Nodes (6): additionalProperties, description, required, $schema, title, type

### Community 55 - "Request Candidate Properties"
Cohesion: 0.29
Nodes (7): $ref, properties, candidate, request_id, pattern, title, type

### Community 56 - "Candidate Domain Definition"
Cohesion: 0.29
Nodes (7): additionalProperties, description, required, title, type, $defs, CardPaymentNoticeCandidate

### Community 57 - "Finals Task Prompt"
Cohesion: 0.29
Nodes (6): Share URL, SHA, usage scope and remaining work, Independent implementation with mocks while waiting for actual connection, Main promotion requires separate explicit user request, Task PRs target phase/Wn; planning PRs target integration, Finals role, task ID, acceptance criteria and predecessor PR, Separate local EVM verification from mocks and reread final state

### Community 58 - "Analyzer Test Fixtures"
Cohesion: 0.38
Nodes (5): cases(), mock_environment(), normal_case(), fixture, socket

### Community 59 - "CI Quality Gates"
Cohesion: 0.33
Nodes (5): Foundry contract tests, Generated schema and golden fixture freshness, Locked Python, pnpm and Foundry dependencies, Python quality and repository structure checks, Web lint, types, tests, build and Playwright

### Community 60 - "Analyzer Ownership Memory"
Cohesion: 0.33
Nodes (5): AI candidate extraction only, CardPaymentNoticeCandidate regression, Mock provider default and explicit live tests, AI only extracts candidate fields, Role D: analyzer, synthetic fixtures and independent QA

### Community 61 - "Portfolio Contribution Records"
Cohesion: 0.33
Nodes (6): 동일 RC 리허설 3회·다른 노트북 재현, 개인·협업·AI 기여 근거, 개인 기여와 포트폴리오 기록, PR → 개인 단계 기록 → 단계 완료 PR·고정 SHA, 동결된 phase/Wn 포트폴리오 결과, 실제 작성자 외 사실 확인

### Community 62 - "Historical Reader Interface"
Cohesion: 0.33
Nodes (6): BlockchainReader 문자열 포트, DependencyUnavailableError, M3 M4 실행 문서 체인 신뢰 상태 통합, 과거 M3 Contract / M4 배포·Reader 경계, keccak256(utf8(identifier)), Indexer 비권위 projection

### Community 63 - "MVP Demo Commands"
Cohesion: 0.33
Nodes (6): make demo-reset 합성 상태 재생성, make demo-stop 데이터 보존, MVP 3-minute demo, make demo 전체 서비스 기동, 금액 변조 TAMPERED + AMOUNT_MISMATCH, 정상 합성 카드 VERIFIED + ACTIVE

### Community 64 - "Missing Field Schema"
Cohesion: 0.33
Nodes (6): type, items, title, type, properties, missing_fields

### Community 65 - "Envelope Schema Definition"
Cohesion: 0.33
Nodes (5): additionalProperties, required, $schema, title, type

### Community 66 - "Missing Field Items"
Cohesion: 0.33
Nodes (6): properties, type, items, title, type, missing_fields

### Community 67 - "Proof Identifier Schema"
Cohesion: 0.33
Nodes (6): anyOf, default, pattern, title, type, proof_id

### Community 68 - "Historical Contract Prompt"
Cohesion: 0.33
Nodes (5): Archived M3 blockchain core instructions, Active, suspended, revoked and irreversible key revocation, No raw Proof or personal data on-chain, Historical Issuer and Issuer Key registries, Foundry unit, fuzz, authorization, transition and event tests

### Community 69 - "Cross Review Procedure"
Cohesion: 0.33
Nodes (5): Cross-review in clean worktree or clone, Mock success does not prove actual chain or browser integration, Check privacy, permissions, AI decision prohibition, v1 regression and v2 policy, Same SHA, lockfile, Schema, ABI and deployment for reproduction, Hold retransmission and follow Operation recovery after uncertain submission

### Community 70 - "Environment Prerequisite Regression"
Cohesion: 0.33
Nodes (4): EnvironmentCheckTest, The supported container workflow does not require host Foundry., unittest, unittest_mock

### Community 71 - "Historical Reader Handoff"
Cohesion: 0.40
Nodes (5): BlockchainReader, DependencyUnavailableError, Handoff: M1 to M4 — BlockchainReader implementation, IssuerRecord, KeyRecord

### Community 72 - "Historical Bootstrap Procedure"
Cohesion: 0.40
Nodes (5): 합성 로컬 Docker 볼륨 demo-reset, Bootstrap runbook, 환경 fingerprint comparable 비교, 과거 Bootstrap 동일 SHA 환경 준비, Alembic·idempotent 합성 Proof seed

### Community 73 - "Contract Ownership Policy"
Cohesion: 0.40
Nodes (5): 체인 원자적 consume·직접 무권한 호출 거부, Contract Agent Instructions, 본선 gateway·commitment·binding 권한, B Issuer/Key/ProofStatus Registry 책임, Claude Code Entry Point

### Community 74 - "Candidate Confidence Bounds"
Cohesion: 0.40
Nodes (5): maximum, minimum, title, type, confidence

### Community 75 - "Application Domain Bounds"
Cohesion: 0.40
Nodes (5): maxLength, minLength, title, type, app_domain

### Community 76 - "Card Domain Definition"
Cohesion: 0.40
Nodes (5): additionalProperties, required, title, type, CardPaymentNotice

### Community 77 - "Masked Card Format"
Cohesion: 0.40
Nodes (5): properties, pattern, title, type, masked_card

### Community 78 - "Issuer Name Bounds"
Cohesion: 0.40
Nodes (5): maxLength, minLength, title, type, issuer_name

### Community 79 - "Merchant Name Bounds"
Cohesion: 0.40
Nodes (5): maxLength, minLength, title, type, merchant

### Community 80 - "Nonce Field Bounds"
Cohesion: 0.40
Nodes (5): maxLength, minLength, title, type, nonce

### Community 81 - "Transaction Identifier Bounds"
Cohesion: 0.40
Nodes (5): transaction_id, maxLength, minLength, title, type

### Community 82 - "Confidence Range Schema"
Cohesion: 0.40
Nodes (5): maximum, minimum, title, type, confidence

### Community 83 - "Historical Backend Prompt"
Cohesion: 0.40
Nodes (4): Archived M1 backend instructions, Historical FastAPI proof storage and deterministic verification ownership, Historical VERIFIED + ACTIVE and TAMPERED + AMOUNT_MISMATCH cases, Historical mock Chain and Analyzer ports

### Community 84 - "Historical Analyzer Prompt"
Cohesion: 0.40
Nodes (4): Archived M2 AI instructions, Refusal, incomplete, timeout, rate limit and schema mismatch handling, Historical LLMProvider, OpenAILLMProvider and MockLLMProvider implementation, Responses API with Pydantic Structured Outputs

### Community 85 - "Historical Integration Prompt"
Cohesion: 0.40
Nodes (4): Archived M4 blockchain integration instructions, Block number and log index event idempotency, Historical deployment, ABI export and BlockchainReader adapter, Explicit mock port until M3 ABI is final

### Community 86 - "Schema Generation Pipeline"
Cohesion: 0.80
Nodes (4): main(), typescript_interface(), typescript_type(), write_types()

### Community 87 - "Development Entry Instructions"
Cohesion: 0.40
Nodes (4): Actual tests, independent review and individual evidence, Finals development entrypoint after completed MVP Gate, Historical bootstrap and MVP records, Independent implementation using agreed contracts and mocks

### Community 88 - "Serena Workspace Configuration"
Cohesion: 0.83
Nodes (3): Gitignore-aware workspace indexing, Python language server, OriginProof Serena project

### Community 90 - "Web Runtime Dependencies"
Cohesion: 0.50
Nodes (4): dependencies, next, react, react-dom

### Community 91 - "Historical Integration Sequence"
Cohesion: 0.50
Nodes (4): MVP 통합 실행 순서, MVP 체인 브랜치 scaffold 삭제 차이 정리, a1a671b MVP 통합·독립 환경 재현 기록, 과거 M1~M4 통합 실행 순서

### Community 92 - "Synthetic Fixture Ownership"
Cohesion: 0.50
Nodes (4): Fixture Agent Instructions, C 생성기·B 체인 검토 Golden Fixture, 합성 F01~F15 사례, Claude Code Entry Point

### Community 93 - "amount minor Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, amount_minor

### Community 94 - "approved at Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, approved_at

### Community 95 - "currency Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, currency

### Community 96 - "issuer name Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, issuer_name

### Community 97 - "masked card Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, masked_card

### Community 98 - "merchant Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, merchant

### Community 99 - "proof id Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, proof_id

### Community 100 - "transaction id Schema"
Cohesion: 0.50
Nodes (4): transaction_id, anyOf, default, title

### Community 101 - "amount minor Schema"
Cohesion: 0.50
Nodes (4): exclusiveMinimum, title, type, amount_minor

### Community 102 - "approved at Schema"
Cohesion: 0.50
Nodes (4): format, title, type, approved_at

### Community 103 - "chain id Schema"
Cohesion: 0.50
Nodes (4): exclusiveMinimum, title, type, chain_id

### Community 104 - "currency Schema"
Cohesion: 0.50
Nodes (4): pattern, title, type, currency

### Community 105 - "expires at Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, expires_at

### Community 106 - "issued at Schema"
Cohesion: 0.50
Nodes (4): format, title, type, issued_at

### Community 107 - "issuer id Schema"
Cohesion: 0.50
Nodes (4): pattern, title, type, issuer_id

### Community 108 - "key id Schema"
Cohesion: 0.50
Nodes (4): pattern, title, type, key_id

### Community 109 - "metadata hash Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, metadata_hash

### Community 110 - "payload hash Schema"
Cohesion: 0.50
Nodes (4): pattern, title, type, payload_hash

### Community 111 - "proof id Schema"
Cohesion: 0.50
Nodes (4): pattern, title, type, proof_id

### Community 112 - "schema version Schema"
Cohesion: 0.50
Nodes (4): schema_version, default, title, type

### Community 113 - "signature Schema"
Cohesion: 0.50
Nodes (4): signature, pattern, title, type

### Community 114 - "single use Schema"
Cohesion: 0.50
Nodes (4): single_use, default, title, type

### Community 115 - "subject binding hash Schema"
Cohesion: 0.50
Nodes (4): subject_binding_hash, anyOf, default, title

### Community 116 - "amount minor Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, amount_minor

### Community 117 - "approved at Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, approved_at

### Community 118 - "currency Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, currency

### Community 119 - "issuer name Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, issuer_name

### Community 120 - "masked card Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, masked_card

### Community 121 - "merchant Schema"
Cohesion: 0.50
Nodes (4): anyOf, default, title, merchant

### Community 122 - "transaction id Schema"
Cohesion: 0.50
Nodes (4): transaction_id, anyOf, default, title

### Community 123 - "Node Workspace Build Policy"
Cohesion: 0.50
Nodes (3): esbuild enabled; sharp and unrs-resolver disabled, packages/sdk workspace, apps/web workspace

### Community 125 - "Documentation Ownership Policy"
Cohesion: 0.67
Nodes (3): Documentation Agent Instructions, 개발 계획 기준본과 ADR 연계, Claude Code Entry Point

### Community 126 - "Historical Candidate Contract"
Cohesion: 0.67
Nodes (3): CardPaymentNoticeCandidate, Handoff: M1 to M2 — Card payment notice candidate contract, 후보 추출과 최종 진위 판정 분리

### Community 129 - "Python Workspace Packages"
Cohesion: 0.67
Nodes (3): originproof-analyzer, originproof-api, originproof-core

## Knowledge Gaps
- **533 isolated node(s):** `originproof-api`, `metadata`, `FormState`, `ApiError`, `normalPreset` (+528 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 680 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `OriginProof 통합 개발 계획서` connect `Finals Development Plan` to `Finals Cryptographic Contracts`, `Historical Extraction Handoff`, `Historical Reader Handoff`, `Historical Bootstrap Procedure`, `Historical Chain Handoffs`, `W3 Issuance Integration`, `W2 Institution Operations`, `W7 Release Rehearsal`, `Historical Reader Interface`, `W5 Role Integration`, `W4 Lifecycle Consume`, `W6 Recovery Verification`, `Historical Integration Sequence`, `W1 Authentication Contracts`, `Portfolio Contribution Records`, `Historical Candidate Contract`, `MVP Demo Commands`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Why does `properties` connect `Proof Envelope Properties` to `Envelope Schema Definition`, `chain id Schema`, `expires at Schema`, `issued at Schema`, `Application Domain Bounds`, `issuer id Schema`, `key id Schema`, `metadata hash Schema`, `payload hash Schema`, `Nonce Field Bounds`, `proof id Schema`, `schema version Schema`, `signature Schema`, `single use Schema`, `subject binding hash Schema`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `SemanticInput` (e.g. with `create_app()` and `LLMProvider`) actually correct?**
  _`SemanticInput` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `AnalyzerError` (e.g. with `evaluate()` and `MockLLMProvider`) actually correct?**
  _`AnalyzerError` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `VerificationService` (e.g. with `test_live_healthcheck()` and `test_malformed_request_has_safe_error_body()`) actually correct?**
  _`VerificationService` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `JsonRpcBlockchainReader` (e.g. with `DependencyUnavailableError` and `IssuerRecord`) actually correct?**
  _`JsonRpcBlockchainReader` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `originproof-api`, `metadata`, `FormState` to the rest of the system?**
  _533 weakly-connected nodes found - possible documentation gaps or missing edges._
## Extraction limitations

Semantic extraction used the current agent session; token usage and cost were not measured. Zero token counters in generator metadata are placeholders, not measured usage. Raw extraction diagnostics reported 196 dangling-endpoint edges, 8 external references, 3 self-loops, and 50 same-endpoint edge collapses in the undirected graph. Graphify may synthesize unresolved symbol nodes and combine relations; verify implementation details in source files. Historical MVP documents remain archived evidence, not current instructions.
