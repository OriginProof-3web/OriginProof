# 5.1 C 후속 구현·재사용 기준

- 작업: V5-W1-C → V5-W2-C → V5-W3-C → V5-W4-C → V5-W5-C.
- 사용자 요청: 재사용 기준 확정, #50 nonce 수정 반영, 공유 계약에 따른 신규 DB/API 개발.
- 기준 integration: `33bc4f4e7456c5ef7c2df8c8bf09f8014e0169f8` (#56 MERGED).
- 재사용 작업본: `ba8946ce1efaeb76946b77064490364a59f0d29e`. 기준 integration을 포함한 C 누적본이며 사용자 변경 없이 시작했습니다.
- 계약: [v5-shared-0.1](../shared_contract_v5.md), [ADR 0004](../adr/0004-v5-governance-wallet-versioning.md). 계약 검토와 실제 체인/웹 연결 완료는 별도입니다.

| 원본 | 채택 범위 | 중복·후속 경계 |
| --- | --- | --- |
| C6 `3ef1fd40943914c1450e8bc05047119ab7eabbc0` | 인증/CSRF/권한·기존 API/DB·Operation·복구·보안/CI·v1/v2 회귀 | 이 작업본의 해당 기능 소스와 동일합니다. #37 `9651062`가 포함돼 있어 다시 복사하지 않습니다. 서버 기관키는 레거시 한정입니다. |
| B #50 `7e75986d68dc7e8b60b4a088f232c8ab26819716` | 제출 전 save_prepared 실패/취소의 nonce 해제·두 회귀 검사 | 새 Writer 전체로 덮지 않습니다. C6의 tx binding/UNKNOWN 보호를 유지합니다. 사용자 요청으로 해당 B 소유 경로의 보완도 수행합니다. |
| B6 `1a7370718a385553c47a0bbae16b7b5639b5f2be` | 기존 Writer/Reader·projection·배포 식별·복구 자산 | C6의 조상입니다. 새 Registry/ABI와의 실제 연결은 B 후속이며 기존 구현을 새 Registry 성공으로 취급하지 않습니다. |
| A5 `56dbd82407e7d04cca97162aebbf276ec6a9f607` | official 웹·QR·오류·접근성의 후속 연결 기준 | A 소스를 이 C API 작업본에 복제하지 않습니다. #54/#48/#53이 포함되므로 별도 전체 반영하지 않습니다. |
| D43 `c16de660914389ba8821612aa3d6c64708085185` | 후보 확인·추출 안전성·provider 경계 참고 | 새 피싱 분석·grounding 완료가 아닙니다. D 분석기를 주입하는 API 경계와 공통 보관/오류를 구현합니다. |
| #56 `b0e0f345fd360e61b98f6e36cf9a57a1bf0d7acd` | wallet 원본 모델·서명·생성물·Golden | 이미 포함돼 있습니다. API /v3와 서명/domain/schema 버전은 별개이며 구자료를 재해석하지 않습니다. |

## 변경 범위와 검사

기존 `apps/`, `packages/`, `scripts/`, `docs/`를 사용합니다. 신규 기관 업무키를 서버에서 생성/보관하지 않으며 체인 확인 불가를 성공으로 대체하지 않습니다. 미선정 입력·Decisions API·공개 배포·기존 DB 삭제는 추가하지 않습니다.

검사는 기존 pytest/Foundry/Node·생성 명령을 재사용합니다. SQLite/ASGI/합성 Adapter 검사와 실제 PostgreSQL·RPC/Registry·브라우저·유료 모델 검사를 구분합니다. 새 DB migration은 기존 자료를 변경하지 않는 추가 테이블 방식으로 준비합니다. 독립 수용 검사·리뷰·실제 연결 근거가 없으면 단계 완료로 판정하지 않습니다.

## 진행 기록

- 재사용 기준: 위 원본·중복·책임 경계를 확정했습니다.
- nonce 보완: #50의 제출 전 예약 해제와 실패/취소 두 회귀를 반영했습니다. 제출 결과 UNKNOWN의 예약 유지도 검사했습니다. Writer+기존 API 회귀 62 PASS, Ruff·diff 검사 통과입니다. 실제 RPC/기관 지갑 연결 검사는 아닙니다.
- DB/API 후속 구현·검사와 baseline 보완 기록은 아래에 있습니다.

### W2 C 독립 구현

합성 명부·데모 메일 코드·지정 내부 승인·키 challenge/서명 증명·공동승인 준비/조회·실제 tx 대조 API와 추가 migration `20261015_0007`을 구현했습니다. 신규 기관 개인키를 생성하거나 단일 운영자로 활성화하지 않습니다. `WalletRegistry` port는 B가 실제 ABI/배포·canonical receipt/event/state 검증 Adapter로 연결하며, 미연결 시 503입니다.

신규 HTTP/SQLite/EIP-712 6개 검사와 기존 회귀를 포함해 454 PASS/6 live SKIP입니다. 임시 PostgreSQL에서 전체 upgrade·schema check·0007→0006→0007 왕복을 통과했습니다. 기존 Alembic 대상에서 빠졌던 projection metadata를 함께 등록해 자동생성이 기존 체인 테이블 삭제를 제안하지 않도록 했습니다. 실제 Registry·브라우저·작성자 외 리뷰는 후속입니다.

### W3 C 독립 구현

초안 원본·EIP-712 검증·기관 서명/Operation의 제출 전 저장, 중계 또는 기관 직접 제출의 tx 대조·UNKNOWN 재조회, 공개 문서·원본/필드/ID 검사와 독립 검증 자료 API를 구현했습니다. 발행은 직접 제출을 기본으로 하며 원본·서명 접수만으로 체인 확정을 표시하지 않습니다. 직접 거래의 request ID 충돌과 잘못된 txHash가 정상 서명 요청을 영구 무효화하지 않는지도 검사합니다.

신규 HTTP 사례 15개를 포함한 해당 API/코어 회귀 65 PASS입니다. 임시 PostgreSQL에서 `0008` upgrade/schema check를 통과했습니다. 원본 bytes·보호 필드·기관 메타데이터/표시명 조작을 분리 검출하고, ID 단독/부분 비교와 RPC 미확인은 INCONCLUSIVE입니다. 새 Registry Adapter는 미연결이며 실제 체인/브라우저 E2E·B/A/D 리뷰는 아직 없습니다.

### W4 C 독립 구현

정확한 latest+1의 초안/제출 검사, 같은 기관의 문서 소유 고정, 버전별 불변 원본, 별도 Revoke EIP-712 요청/제출을 추가했습니다. 기관 정지 중에도 현재 비사고 키의 철회를 허용하고 정상 교체의 과거 서명·현재 사고 경고를 구분합니다. 원자적 버전 전이는 B Registry의 검증된 상태/이벤트를 소비하며 API가 DB의 최신 포인터를 권위로 만들지 않습니다.

신규 HTTP 사례 누적 20 PASS입니다. 다음 버전·과거 대체·최신 철회 후 미복구·동일 nonce 경쟁 거부·타 기관·정지/철회·구키 신규 서명 거부·과거 정상 서명/사고 경고·서로 다른 승인자 1/2/중복 결과를 검사했습니다. 합성 Registry 근거이며 실제 컨트랙트의 원자성·브라우저 연결이나 소유자 리뷰를 대신하지 않습니다.
### 2026-10-18 W2 리뷰 보완

이메일 검증값은 `API_WALLET_EMAIL_SECRET`의 최소 32바이트 서버 비밀을 사용하는
HMAC-SHA256으로 바꿨습니다. 비밀은 Settings repr/직렬화·응답에서 제외하며 기관 지갑키와
무관합니다. 설정이 없으면 코드 발급·검증을 성공시키지 않습니다. 이전 SHA 검증값은
확인하지 않고 무효화해 재발급합니다. 기존 만료/재발급/누적 실패 제한과 원자적 소비를
유지하고, 만료·소비·5회 실패 시 검증값/데모 평문을 지웁니다. 시작 시와 정상 가동 중
300초 간격으로 만료 코드를 정리하며, 조회·검증에서도 만료 직후 접근을 차단합니다.

KeyProof 없는 REACTIVATE는 공유 ABI의 0값 tuple과 빈 bytes를 전달하도록 W5 보완을
이 단계로 앞당겼습니다. API가 실제 저장한 인자를 커밋된 인터페이스 ABI와 Foundry cast로
인코딩하는 회귀를 추가했습니다. cast 없는 환경에서는 해당 검사는 명시적으로 skip합니다.
원본/소비자·기존 계약 변경은 없으며 실제 B Registry·지갑 연결 검사는 별도입니다.

이 보완 소스의 전체 Python 검사(API·core·analyzer·indexer·scripts/ci)는 463 PASS /
8 live opt-in SKIP / 기존 Starlette 경고 1건입니다. Ruff·diff 검사도 통과했습니다.

### 2026-10-18 W3 리뷰 보완

철회 확정은 요청의 기관·doc_key·documentId·version과 실제 REVOKED 효과가 모두 같을 때만
허용합니다. SUPERSEDED/ACTIVE/EXPIRED 및 다른 문서·버전은 UNKNOWN으로 유지합니다.
이 단계에 아직 철회 HTTP 경로가 없으므로 공통 확정 함수를 실제 저장 요청·서명·receipt와
대조하는 8개 거부/성공 회귀로 먼저 검사했고 W4에서 HTTP 경로를 추가 검사합니다.
서명 뒤 미전송 작업은 RECONCILE을 안내하고 deadline 후 원래 요청·체인 nonce·문서 부재를
확인한 경우에만 예약을 끝내 RESIGN을 안내합니다. 새 전송은 수행하지 않습니다.

API·코어 162 PASS / 4 live opt-in SKIP, 신규/기존 wallet HTTP·저장 검사 32 PASS,
Ruff 통과입니다. 실제 Registry·브라우저 연결 완료와 구분합니다.

### 2026-10-18 W4 리뷰 보완

철회 HTTP 경로에서 SUPERSEDED 문서와 성공 receipt만 관측하면 UNKNOWN을 유지하는
사례를 추가했습니다. 이후 같은 원래 거래의 REVOKED 효과가 관측되면 재전송 없이
CONFIRMED로 복구합니다. 기존 성공 helper는 관측 상태를 인자로 받아, 항상 REVOKED를
먼저 주입하는 테스트 공백을 없앴습니다. wallet HTTP·저장 및 core 검사 81 PASS,
Ruff 통과이며 실제 EVM 원자성·경쟁 성공을 뜻하지 않습니다.
- DB/API·후속 연결: #59~#63의 후속 브랜치에 구현·검사 기록이 있습니다.
  이 baseline에는 신규 지갑 API가 없으며 후속 구현을 완료한 것으로 표시하지 않습니다.

## 2026-10-18 baseline 리뷰 보완

공식 integration `5470558`(#80 포함)을 병합해 CI/indexer 수집과 D의 기존 자료를
보존했습니다. `fixtures/finals/README.md` 충돌은 W3 자료와 V5 D QA 설명을 모두 유지해
해결했습니다. #58 nonce 실패/취소 회귀도 baseline에 포함돼 있습니다.

0006은 현재 projection 모델을 런타임 import하지 않고 당시와 같은 네 테이블 정의를
revision 안에 고정했습니다. revision ID·DDL·적용된 DB는 바꾸지 않습니다. 이미 적용한 DB는
재실행하지 않으며 데이터 변환·새 테이블 변경은 새 revision으로 합니다. 재적용의 projection
자료 보존, 모델 DDL 일치, downgrade 시 API 자료 보존을 회귀로 검사합니다. Alembic 대상에는
projection metadata도 등록해 자동생성이 기존 체인 테이블 삭제를 제안하지 않게 했습니다.

레거시 readiness는 미리 등록된 MVP 기관과 신규 발행 기관 ID가 충돌하는 설정을 거부합니다.
`.env.example`의 분리된 두 ID를 사용해야 하며 신규 지갑 모드에는 이 레거시 배포 조건을
적용하지 않습니다. Compose secret 경로도 `/workspace/build/secrets`로 정정했습니다.

레거시 P0는 API 세션으로 기관을 구분하고 공통 EVM 호출자를 사용합니다. 이를 기관별 체인
권한 검증 성공으로 간주하지 않습니다. 수신자 목록은 합성 데모 공용 주소록이라는 기존 범위를
명시했습니다. 기관별 주소록·체인 역할 재설계·A 화면 보완은 이 baseline에서 추가하지 않습니다.
과거 lifecycle 표시·서명 시각 정책은 해당 ADR/담당 리뷰로 남기며 지갑 정책으로 소급하지 않습니다.
기존 phase 보존 및 작업→단계→integration 흐름을 유지하고 #77은 검증 후보로만 사용합니다.

이 baseline의 전체 Python 검사 494 PASS / 8 SKIP / 기존 Starlette 경고 1건,
Ruff·diff 검사 통과입니다. 실제 기존 DB의 변경·다운그레이드는 실행하지 않았습니다.
