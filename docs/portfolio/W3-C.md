# W3 C — 두 유형 발행·조회·검증

C / @Jordi2801K, W3-C1/C2/C3. 기준 phase/W2@1f8ed63, 작업 feat/w3-c-issuance.
구현·자체 및 실제 DB/체인 HTTP 검사 완료; A 화면 연결·B 교차 리뷰·D 독립 검증 대기.

C가 발행 API·원자적 저장/migration·수신자 binding 권한·typed 공개/제한 조회·코어/RPC 연결·검사를 구현했습니다.
B의 기존 Reader/Writer/manifest와 C의 W1 v2 코어·W2 signer/Operation을 재사용했습니다.
A/B/D 경로 구현·타인의 리뷰를 수행했다고 기록하지 않습니다. Codex가 구현·검사·원인 분석을 보조했습니다.

하나의 DB transaction과 W2 advisory lock을 재사용해 중복 발행과 교체 중 키 선택 충돌을 막았습니다.
수신자 token은 계정마다, salt는 Proof마다 생성하고 공개 응답에서 제외합니다.
별도 v2 테이블로 v1 회귀를 보존하며, 아직 없는 Proof 상태는 NOT_RUN/null로 명시합니다.
테스트 초기 실패는 합성 Reader의 Pydantic 위치 인자 사용과 optional 인증 테스트 경계에서 발생했으며,
키워드 모델 구성·FastAPI dependency로 수정 후 재검증했습니다.

전체 Python 236 passed / live opt-in 5 skipped, Ruff 통과.
실제 분리 PostgreSQL 16·Anvil 1.4.4 HTTP 검사 1 passed: 두 유형 새 서명/저장,
동시 동일 ID, 공개/수신자 조회·정상/변조 비교. migration/모델 check 통과.
macOS/Python 3.13 환경, 합성 계정·임시 DB/chain만 사용했습니다. 성능·실제 브라우저·타인 리뷰는 미측정/미실행입니다.
상세 계약·재현 원본: [W3 API 인계](../api/w3_c_proof_contract.md).
최종 코드와 실제 CI SHA는 작업 PR에서 확인하며 단계 전체 완료는 선언하지 않습니다.


## 2026-10-02 W3-B1 연결 보완

W4 후속 branch `feat/w4-c-proof-lifecycle`의 C 코드 `596f313`에서 B W3 `92e0e94`의
get_issuer_key_snapshot을 발행·검증에 연결했습니다. 기관과 키의 동일 block/hash,
발행 직전 유효 구간·signer를 검사하고 Proof 상태 snapshot과도 일관성을 확인합니다.
이 branch에서는 W4 Registry가 연결되어 위 W3 최초 결과의 NOT_RUN/null 한계를 대체합니다.
C 자체 실제 DB/체인 검사는 통과했으며 A 화면·D 독립 확인·공유 phase 병합·팀 리뷰는 대기입니다.
[후속 연결·검사 상세](../api/w4_c_proof_lifecycle_contract.md)를 참조합니다.

## 2026-10-18 V5-W3-C 셀프 리뷰 후속

C / @Jordi2801K의 요청으로 Codex가 만료·재시도 반례와 최소 수정을 보조했습니다.
Operation 누락은 서명 재제출·직접 거래 양쪽에서 410으로 처리하고, 새 ID로 기존 서명을
재시도할 때 기존 WalletRequestRow에 fingerprint·Operation 연결을 보존했습니다.
같은 ID·같은 입력은 동일 Operation, 다른 발행 입력은 409이며 새 ID의 정상 발행은 유지합니다.
해당 wallet HTTP·저장 검사 36 PASS 및 Ruff·diff 검사 통과입니다. 실제 지갑 연결이나
다른 팀원의 리뷰 완료를 의미하지 않습니다. 후속 W4~W6 및 #77에 순방향으로 반영합니다.

## 2026-10-18 확대 감사 Operation·복구 보완

RPC 전후의 최신 행 잠금·해시 binding으로 늦은 거래가 확정을 덮어쓰지 못하게 했습니다.
알려진 해시를 먼저 재조회하고 잘못된 미검증 후보는 검색으로 복구하며, 만료 정각부터
조회·재요청·직접 접수·복구를 차단합니다. 기존 v1 목록·감사 필터는 pagination 전에 적용합니다.
W2의 proof 선행조건과 새 HTTP 회귀 27개를 포함한 W3 전체 검사는
557 PASS / 8 opt-in SKIP / 기존 경고 1개입니다. W3 응답 모델을 유지해 후속 필드를 앞당겨 넣지 않았습니다.
실제 지갑·B Adapter 연결과 사람의 독립 리뷰는 별도입니다.
