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
- DB/API·후속 연결: 해당 구현 커밋과 실행 결과를 아래에 갱신합니다.

### W2 C 독립 구현

합성 명부·데모 메일 코드·지정 내부 승인·키 challenge/서명 증명·공동승인 준비/조회·실제 tx 대조 API와 추가 migration `20261015_0007`을 구현했습니다. 신규 기관 개인키를 생성하거나 단일 운영자로 활성화하지 않습니다. `WalletRegistry` port는 B가 실제 ABI/배포·canonical receipt/event/state 검증 Adapter로 연결하며, 미연결 시 503입니다.

신규 HTTP/SQLite/EIP-712 6개 검사와 기존 회귀를 포함해 454 PASS/6 live SKIP입니다. 임시 PostgreSQL에서 전체 upgrade·schema check·0007→0006→0007 왕복을 통과했습니다. 기존 Alembic 대상에서 빠졌던 projection metadata를 함께 등록해 자동생성이 기존 체인 테이블 삭제를 제안하지 않도록 했습니다. 실제 Registry·브라우저·작성자 외 리뷰는 후속입니다.
