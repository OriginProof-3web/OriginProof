# Graph Report - OriginProof  (2026-09-28)

## Corpus Check
- Corpus is ~33,579 words - fits in a single context window. You may not need a graph.

## Summary
- 930 nodes · 1610 edges · 104 communities (86 shown, 18 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 168 edges (avg confidence: 0.93)
- Token cost: 11,100 input · 2,360 output

## Community Hubs (Navigation)
- Canonicalization and Signatures
- Deployment and RPC Tooling
- Verification Result Schema
- Blockchain Reader
- Card Notice Schema
- Analyzer Errors and Providers
- Project Docs and Infrastructure
- Analyzer Extraction Tests
- Database and Event Projection
- Web App Tests
- OpenAI Adapter Tests
- TypeScript Compiler Setup
- Verification API
- Synthetic Image Evaluation
- API Trust-State Checks
- Demo Verification Page
- Candidate Input Contracts
- Web Tooling Dependencies
- Analyzer Provider Internals
- Signed Proof Persistence
- Database Migration Setup
- Generated TypeScript Contracts
- Proof Type Enumerations
- JSON Schema References
- Analyzer Ownership and Handoff
- Verification Domain Concepts
- Web Package Scripts
- Next.js Root Layout
- ESLint Configuration
- Root Package Scripts
- Candidate Payload Schema
- Verification Request Schema
- API Candidate Request Fields
- Candidate Required Fields
- Local Proof Seed Workflow
- Proof Storage Smoke Test
- Database Lifecycle
- Runtime Configuration
- Generic Schema Types
- Signed Proof Envelope Schema
- Schema Property Definitions
- Optional Candidate Values
- Amount Range Constraints
- Candidate String Length Rules
- Schema Required Properties
- Schema Pattern Validation
- Identifier Length Rules
- Masked Card Length Constraints
- Merchant Field Constraints
- Transaction Identifier Constraints
- Chain ID Range Constraints
- MVP Role Ownership
- End-to-End Accessibility Tests
- Frontend Runtime Dependencies
- CI and Review Workflows
- Amount Candidate Field
- Approval Timestamp Field
- Currency Candidate Field
- Issuer Name Field
- Masked Card Field
- Merchant Candidate Field
- Proof ID Field
- Transaction ID Candidate Field
- Amount Minor Units
- Approval Timestamp Format
- Chain ID Validation
- Currency Pattern
- Proof Expiry Field
- Issued Timestamp Field
- Issuer Identifier Pattern
- Key Identifier Pattern
- Metadata Hash Field
- Payload Hash Pattern
- Proof ID Pattern
- Schema Version Field
- Signature Pattern
- Single Use Flag
- Subject Binding Hash
- Notice Amount Field
- Notice Approval Timestamp
- Notice Currency Field
- Notice Issuer Name
- Notice Masked Card
- Notice Merchant
- Notice Transaction Identifier
- Web Application Instructions
- Candidate Model Validation
- Python Workspace Packages
- Team Bootstrap and Environment
- Analyzer Validation Tests
- API Package
- Generated Next.js Types
- Documentation Ownership
- Fixture Ownership
- Infrastructure Ownership
- Contract Ownership
- Shared Core Ownership
- Schema Generation Ownership
- Smoke Test Script
- Analyzer Package
- MVP Architecture
- Foundry Configuration
- Python Workspace Configuration
- Historical Analyzer Audit

## God Nodes (most connected - your core abstractions)
1. `SemanticInput` - 42 edges
2. `AnalyzerError` - 35 edges
3. `VerificationService` - 34 edges
4. `JsonRpcBlockchainReader` - 28 edges
5. `MockLLMProvider` - 22 edges
6. `SemanticInterface` - 22 edges
7. `DependencyUnavailableError` - 20 edges
8. `create_app()` - 20 edges
9. `SignedProofEnvelope` - 19 edges
10. `create_app()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `deploy()` --calls--> `address()`  [INFERRED]
  packages/contracts/script/deploy_local.py → apps/api/src/infrastructure/blockchain/reader.py
- `JsonRpcBlockchainReader` --uses--> `IssuerRecord`  [INFERRED]
  apps/api/src/infrastructure/blockchain/reader.py → packages/python/originproof_core/ports.py
- `JsonRpcBlockchainReader` --uses--> `IssuerTrustStatus`  [INFERRED]
  apps/api/src/infrastructure/blockchain/reader.py → packages/python/originproof_core/ports.py
- `JsonRpcBlockchainReader` --uses--> `KeyRecord`  [INFERRED]
  apps/api/src/infrastructure/blockchain/reader.py → packages/python/originproof_core/ports.py
- `JsonRpcBlockchainReader` --uses--> `KeyTrustStatus`  [INFERRED]
  apps/api/src/infrastructure/blockchain/reader.py → packages/python/originproof_core/ports.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **MVP verification stack** — docs_api_mvp_verification_verification_api, docs_handoffs_m4_chain_reader_contract_blockchain_reader, docs_blockchain_m3_readme_issuer_registries [EXTRACTED 1.00]

## Communities (104 total, 18 thin omitted)

### Community 0 - "Canonicalization and Signatures"
Cohesion: 0.06
Nodes (68): datetime, enum, eth_keys, eth_keys_exceptions, field_validator, canonical_json_bytes(), _normalize(), payload_hash() (+60 more)

### Community 1 - "Deployment and RPC Tooling"
Cohesion: 0.06
Nodes (40): argparse, AsyncClient, httpx, infrastructure_blockchain_reader, json, os, deploy(), export_abi() (+32 more)

### Community 2 - "Verification Result Schema"
Cohesion: 0.04
Nodes (46): additionalProperties, type, additionalProperties, title, type, $defs, LifecycleStatus, ReasonCode (+38 more)

### Community 3 - "Blockchain Reader"
Cohesion: 0.11
Nodes (25): address(), digest(), JsonRpcBlockchainReader, datetime, M1 port adapter. All registry calls within one operation use the same block., uint(), crypto_hash, itertools (+17 more)

### Community 4 - "Card Notice Schema"
Cohesion: 0.05
Nodes (37): additionalProperties, exclusiveMinimum, title, type, format, title, type, pattern (+29 more)

### Community 5 - "Analyzer Errors and Providers"
Cohesion: 0.11
Nodes (16): Exception, OpenAI, AnalyzerError, Only fixed, safe messages cross the provider boundary., create_app(), capabilities(), invalid_input(), FastAPI (+8 more)

### Community 6 - "Project Docs and Infrastructure"
Cohesion: 0.11
Nodes (25): API Agent Instructions, API Claude Code Entry Point, Docker Compose Services, Local Anvil Chain Service, PostgreSQL Service, MVP Card-Notice Verification API, MVP Verification API, M3 Smart Contract Core (+17 more)

### Community 7 - "Analyzer Extraction Tests"
Cohesion: 0.18
Nodes (19): fastapi_testclient, logging, MockLLMProvider, Template parser and opt-in hash-based image replay; NOT OCR or model…, SemanticInterface, test_invalid_provider_objects_do_not_leak_in_warnings(), image_bytes(), parametrize (+11 more)

### Community 8 - "Database and Event Projection"
Cohesion: 0.13
Nodes (10): alembic, dataclasses, ChainEvent, ProjectionStore, SQLAlchemy event projection; chain state remains authoritative., event(), test_reorg_and_conflicts(), test_restart_replay() (+2 more)

### Community 9 - "Web App Tests"
Cohesion: 0.12
Nodes (15): name, private, version, eslint, eslint-config-next, jsdom, react, react-dom (+7 more)

### Community 10 - "OpenAI Adapter Tests"
Cohesion: 0.23
Nodes (16): make_provider(), fixture, parametrize, The real OpenAI SDK over MockTransport: no API key, external request, or live…, response_body(), test_http_errors_do_not_expose_provider_details(), test_incomplete_truncated_json_keeps_incomplete_error(), test_low_confidence_domain_gate() (+8 more)

### Community 11 - "TypeScript Compiler Setup"
Cohesion: 0.11
Nodes (17): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+9 more)

### Community 12 - "Verification API"
Cohesion: 0.13
Nodes (11): create_app(), invalid_request(), datetime, FastAPI, _request_id(), contextlib, fastapi_exceptions, fastapi_responses (+3 more)

### Community 13 - "Synthetic Image Evaluation"
Cohesion: 0.18
Nodes (14): base64, hashlib, io, pil, evaluate(), run_case(), main(), Path (+6 more)

### Community 14 - "API Trust-State Checks"
Cohesion: 0.21
Nodes (8): UnavailableBlockchainReader, test_live_healthcheck(), test_malformed_request_has_safe_error_body(), test_verification_is_inconclusive_without_configured_adapters(), UnavailableProofRepository, IssuerRecord, KeyRecord, BaseModel

### Community 15 - "Demo Verification Page"
Cohesion: 0.16
Nodes (11): ApiError, asUtc(), baselineProof, checkValue(), DemoPage(), flowSteps, FormState, normalPreset (+3 more)

### Community 16 - "Candidate Input Contracts"
Cohesion: 0.16
Nodes (8): BaseModel, Untrusted input transport model, not an alternative domain Candidate schema., SemanticInput, LLMProvider, _parse_mock_text(), CardPaymentNoticeCandidate, Protocol, CardPaymentNoticeCandidate

### Community 17 - "Web Tooling Dependencies"
Cohesion: 0.14
Nodes (14): devDependencies, @axe-core/playwright, eslint, eslint-config-next, @eslint/eslintrc, jsdom, @playwright/test, @testing-library/jest-dom (+6 more)

### Community 18 - "Analyzer Provider Internals"
Cohesion: 0.27
Nodes (8): importlib_resources, pydantic, AnalyzerErrorCode, StrEnum, CardPaymentNoticeCandidate, Validate transport invariants without modifying or redefining M1's model., validate_candidate(), time

### Community 19 - "Signed Proof Persistence"
Cohesion: 0.22
Nodes (8): Base, SignedProofRow, SignedProofEnvelope, Trusted server-side Signed Proof storage; raw candidate input is never…, SqlAlchemyProofRepository, collections_abc, DeclarativeBase, sqlalchemy_orm

### Community 20 - "Database Migration Setup"
Cohesion: 0.22
Nodes (7): do_run_migrations(), run_migrations_online(), asyncio, logging_config, pydantic_settings, sqlalchemy_ext_asyncio, sqlalchemy_pool

### Community 21 - "Generated TypeScript Contracts"
Cohesion: 0.20
Nodes (9): CardPaymentNotice, CardPaymentNoticeCandidate, LifecycleStatus, ProofType, ReasonCode, SignatureScheme, SignedProofEnvelope, VerificationResult (+1 more)

### Community 22 - "Proof Type Enumerations"
Cohesion: 0.22
Nodes (9): $defs, ProofType, SignatureScheme, enum, title, type, enum, title (+1 more)

### Community 23 - "JSON Schema References"
Cohesion: 0.22
Nodes (9): $ref, default, $ref, properties, payload, proof_type, signature_scheme, default (+1 more)

### Community 24 - "Analyzer Ownership and Handoff"
Cohesion: 0.22
Nodes (9): Analyzer Agent Instructions, CardPaymentNoticeCandidate, Card Payment Notice Extraction, POST /v1/analyze/card-payment-notice, Analyzer Integration Handoff, card_payment_notice_v3 Prompt, OriginProof M2 Analyzer README, Blockchain Integration Agent Instructions (+1 more)

### Community 25 - "Verification Domain Concepts"
Cohesion: 0.29
Nodes (8): AI Candidate Field Extraction, Deterministic Backend Verification, MVP Verification Flow, Issuer and Key Shared Trust State, M1 Backend Implementation, M2 AI Analyzer Implementation, Issuer and Issuer Key Registries, Blockchain Reader Integration

### Community 26 - "Web Package Scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, start, test, test:e2e, typecheck

### Community 27 - "Next.js Root Layout"
Cohesion: 0.29
Nodes (4): metadata, apps_web_app_styles, nextConfig, next

### Community 28 - "ESLint Configuration"
Cohesion: 0.29
Nodes (6): baseDirectory, compat, config, @eslint/eslintrc, ref_node_path, ref_node_url

### Community 29 - "Root Package Scripts"
Cohesion: 0.29
Nodes (6): name, packageManager, private, scripts, lint, typecheck

### Community 30 - "Candidate Payload Schema"
Cohesion: 0.29
Nodes (6): additionalProperties, description, required, $schema, title, type

### Community 31 - "Verification Request Schema"
Cohesion: 0.29
Nodes (6): additionalProperties, description, required, $schema, title, type

### Community 32 - "API Candidate Request Fields"
Cohesion: 0.29
Nodes (7): $ref, properties, candidate, request_id, pattern, title, type

### Community 33 - "Candidate Required Fields"
Cohesion: 0.29
Nodes (7): additionalProperties, description, required, title, type, $defs, CardPaymentNoticeCandidate

### Community 34 - "Local Proof Seed Workflow"
Cohesion: 0.43
Nodes (6): PrivateKey, async_main(), _load_or_create_private_key(), Create a local-only key for synthetic development data, never for production…, read_fixture(), seed()

### Community 35 - "Proof Storage Smoke Test"
Cohesion: 0.38
Nodes (4): main(), datetime, Test-only chain port using the synthetic issuer recorded by the seed., SeededChainReader

### Community 37 - "Runtime Configuration"
Cohesion: 0.47
Nodes (6): configured_blockchain_reader(), BaseSettings, Runtime settings. Secrets are loaded from the environment and never logged., Settings, test_complete_chain_configuration_selects_reader(), test_incomplete_chain_configuration_is_unavailable()

### Community 38 - "Generic Schema Types"
Cohesion: 0.33
Nodes (6): type, items, title, type, properties, missing_fields

### Community 39 - "Signed Proof Envelope Schema"
Cohesion: 0.33
Nodes (5): additionalProperties, required, $schema, title, type

### Community 40 - "Schema Property Definitions"
Cohesion: 0.33
Nodes (6): properties, type, items, title, type, missing_fields

### Community 41 - "Optional Candidate Values"
Cohesion: 0.33
Nodes (6): anyOf, default, pattern, title, type, proof_id

### Community 42 - "Amount Range Constraints"
Cohesion: 0.40
Nodes (5): maximum, minimum, title, type, confidence

### Community 43 - "Candidate String Length Rules"
Cohesion: 0.40
Nodes (5): maxLength, minLength, title, type, app_domain

### Community 44 - "Schema Required Properties"
Cohesion: 0.40
Nodes (5): additionalProperties, required, title, type, CardPaymentNotice

### Community 45 - "Schema Pattern Validation"
Cohesion: 0.40
Nodes (5): properties, pattern, title, type, masked_card

### Community 46 - "Identifier Length Rules"
Cohesion: 0.40
Nodes (5): maxLength, minLength, title, type, issuer_name

### Community 47 - "Masked Card Length Constraints"
Cohesion: 0.40
Nodes (5): maxLength, minLength, title, type, merchant

### Community 48 - "Merchant Field Constraints"
Cohesion: 0.40
Nodes (5): maxLength, minLength, title, type, nonce

### Community 49 - "Transaction Identifier Constraints"
Cohesion: 0.40
Nodes (5): transaction_id, maxLength, minLength, title, type

### Community 50 - "Chain ID Range Constraints"
Cohesion: 0.40
Nodes (5): maximum, minimum, title, type, confidence

### Community 51 - "MVP Role Ownership"
Cohesion: 0.60
Nodes (5): M1 Backend, M2 AI Analyzer, M3 Blockchain Core, M4 Blockchain Integration, MVP End-to-End Flow

### Community 53 - "Frontend Runtime Dependencies"
Cohesion: 0.50
Nodes (4): dependencies, next, react, react-dom

### Community 54 - "CI and Review Workflows"
Cohesion: 0.50
Nodes (4): CI Uses Local Make Targets, Merged Pull Request Discord Notification, GitHub Actions Quality Gate, Clean-Worktree Cross Review

### Community 55 - "Amount Candidate Field"
Cohesion: 0.50
Nodes (4): anyOf, default, title, amount_minor

### Community 56 - "Approval Timestamp Field"
Cohesion: 0.50
Nodes (4): anyOf, default, title, approved_at

### Community 57 - "Currency Candidate Field"
Cohesion: 0.50
Nodes (4): anyOf, default, title, currency

### Community 58 - "Issuer Name Field"
Cohesion: 0.50
Nodes (4): anyOf, default, title, issuer_name

### Community 59 - "Masked Card Field"
Cohesion: 0.50
Nodes (4): anyOf, default, title, masked_card

### Community 60 - "Merchant Candidate Field"
Cohesion: 0.50
Nodes (4): anyOf, default, title, merchant

### Community 61 - "Proof ID Field"
Cohesion: 0.50
Nodes (4): anyOf, default, title, proof_id

### Community 62 - "Transaction ID Candidate Field"
Cohesion: 0.50
Nodes (4): transaction_id, anyOf, default, title

### Community 63 - "Amount Minor Units"
Cohesion: 0.50
Nodes (4): exclusiveMinimum, title, type, amount_minor

### Community 64 - "Approval Timestamp Format"
Cohesion: 0.50
Nodes (4): format, title, type, approved_at

### Community 65 - "Chain ID Validation"
Cohesion: 0.50
Nodes (4): exclusiveMinimum, title, type, chain_id

### Community 66 - "Currency Pattern"
Cohesion: 0.50
Nodes (4): pattern, title, type, currency

### Community 67 - "Proof Expiry Field"
Cohesion: 0.50
Nodes (4): anyOf, default, title, expires_at

### Community 68 - "Issued Timestamp Field"
Cohesion: 0.50
Nodes (4): format, title, type, issued_at

### Community 69 - "Issuer Identifier Pattern"
Cohesion: 0.50
Nodes (4): pattern, title, type, issuer_id

### Community 70 - "Key Identifier Pattern"
Cohesion: 0.50
Nodes (4): pattern, title, type, key_id

### Community 71 - "Metadata Hash Field"
Cohesion: 0.50
Nodes (4): anyOf, default, title, metadata_hash

### Community 72 - "Payload Hash Pattern"
Cohesion: 0.50
Nodes (4): pattern, title, type, payload_hash

### Community 73 - "Proof ID Pattern"
Cohesion: 0.50
Nodes (4): pattern, title, type, proof_id

### Community 74 - "Schema Version Field"
Cohesion: 0.50
Nodes (4): schema_version, default, title, type

### Community 75 - "Signature Pattern"
Cohesion: 0.50
Nodes (4): signature, pattern, title, type

### Community 76 - "Single Use Flag"
Cohesion: 0.50
Nodes (4): single_use, default, title, type

### Community 77 - "Subject Binding Hash"
Cohesion: 0.50
Nodes (4): subject_binding_hash, anyOf, default, title

### Community 78 - "Notice Amount Field"
Cohesion: 0.50
Nodes (4): anyOf, default, title, amount_minor

### Community 79 - "Notice Approval Timestamp"
Cohesion: 0.50
Nodes (4): anyOf, default, title, approved_at

### Community 80 - "Notice Currency Field"
Cohesion: 0.50
Nodes (4): anyOf, default, title, currency

### Community 81 - "Notice Issuer Name"
Cohesion: 0.50
Nodes (4): anyOf, default, title, issuer_name

### Community 82 - "Notice Masked Card"
Cohesion: 0.50
Nodes (4): anyOf, default, title, masked_card

### Community 83 - "Notice Merchant"
Cohesion: 0.50
Nodes (4): anyOf, default, title, merchant

### Community 84 - "Notice Transaction Identifier"
Cohesion: 0.50
Nodes (4): transaction_id, anyOf, default, title

### Community 85 - "Web Application Instructions"
Cohesion: 0.67
Nodes (3): Web Agent Instructions, Web User App and Issuer Console, pnpm Workspace Configuration

### Community 87 - "Python Workspace Packages"
Cohesion: 0.67
Nodes (3): originproof-analyzer, originproof-api, originproof-core

### Community 88 - "Team Bootstrap and Environment"
Cohesion: 0.67
Nodes (3): Bootstrap Integrator, Comparable Environment Fingerprint, Shared Bootstrap Commit SHA

## Knowledge Gaps
- **343 isolated node(s):** `originproof-api`, `metadata`, `FormState`, `ApiError`, `normalPreset` (+338 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 463 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `properties` connect `JSON Schema References` to `Chain ID Validation`, `Proof Expiry Field`, `Issued Timestamp Field`, `Issuer Identifier Pattern`, `Key Identifier Pattern`, `Signed Proof Envelope Schema`, `Metadata Hash Field`, `Payload Hash Pattern`, `Proof ID Pattern`, `Candidate String Length Rules`, `Schema Version Field`, `Signature Pattern`, `Single Use Flag`, `Subject Binding Hash`, `Merchant Field Constraints`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Why does `VerificationService` connect `Canonicalization and Signatures` to `Deployment and RPC Tooling`, `Proof Storage Smoke Test`, `Blockchain Reader`, `Verification API`, `API Trust-State Checks`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Why does `SemanticInput` connect `Candidate Input Contracts` to `Analyzer Errors and Providers`, `Analyzer Extraction Tests`, `OpenAI Adapter Tests`, `Synthetic Image Evaluation`, `Analyzer Provider Internals`, `Candidate Model Validation`, `Analyzer Validation Tests`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `SemanticInput` (e.g. with `create_app()` and `LLMProvider`) actually correct?**
  _`SemanticInput` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `AnalyzerError` (e.g. with `evaluate()` and `MockLLMProvider`) actually correct?**
  _`AnalyzerError` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `VerificationService` (e.g. with `test_live_healthcheck()` and `test_malformed_request_has_safe_error_body()`) actually correct?**
  _`VerificationService` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `JsonRpcBlockchainReader` (e.g. with `DependencyUnavailableError` and `IssuerRecord`) actually correct?**
  _`JsonRpcBlockchainReader` has 14 INFERRED edges - model-reasoned connections that need verification._

> Semantic extraction token counts are partial: only one of three agent results supplied nonzero token counts; other chunks reported placeholders.
