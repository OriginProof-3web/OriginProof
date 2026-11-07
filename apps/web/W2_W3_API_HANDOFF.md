# W2/W3 웹 연결 handoff

작성 기준: `origin/integration@3295a71c10a1a99c523d3cfefde91b5737b737ac`

## 확인된 입력

- W1 계정·기관 신청 초안: PR [#23](https://github.com/OriginProof-3web/OriginProof/pull/23), `feat/w1-c-independent@167e0a9`.
- W2 B Registry/Adapter 초안: PR [#26](https://github.com/OriginProof-3web/OriginProof/pull/26), `codex/w1-b-registry-contract@78411462`.
- W2 C Operation 저장·읽기 초안: `feat/w2-c-operations-prep@89bb658`, `docs/api/w2_c_operation_contract.md`.
- W3 필드와 검증 의미: 승인된 ADR 0001, 1·4~6절.

현재 화면은 W1 신청 검토를 이어가고, C 초안에 있는 `GET /v1/operations/{operation_id}`와 `GET /v1/audit-events`를 읽기 전용으로 조회합니다. `UNKNOWN` 작업은 성공이나 실패로 단정하지 않습니다. 이 변경은 mock 검사이며 API·체인 연결 완료를 뜻하지 않습니다.

## 연결 전 필요한 API/모델 정보

### W2-A1 · 기관 상태 변경과 작업 상태

- 기관 중지·재활성화·영구 폐기의 확정 API 경로, role/CSRF, request ID와 request body.
- 신청 승인과 chain operation 사이의 응답 관계: operation ID, 최종 신청 상태, timeout 뒤 조회/재시도 방법.
- operation 상태의 전체 enum, 제출 시각·확정 block/confirmation·재조회 증거 중 웹에 공개할 필드.
- 기관 목록/상세와 현재 chain/network 상태를 읽는 경로 및 권한 오류 응답.

### W2-A2 · 발행 키

- 서버 서명기 생성과 challenge 검증, 공개키 등록/폐기 경로·입력·응답.
- key ID, 공개 signer, 유효 구간, 키 상태와 선택된 발행 키의 생성 모델/enum.
- 승인 전, 만료, 이미 폐기, 체인 미확정, timeout/retry의 API 오류·operation 연결 규칙.
- 개인키와 secret 참조가 웹 응답·화면에 나오지 않는다는 응답 예시.

### W3-A1/A2 · 발행·목록·QR

- `PAYMENT_REQUEST`와 `OFFICIAL_DOCUMENT`의 생성 TypeScript 타입, 발행 endpoint와 각 유형의 request/response/error 예시.
- 수신자 선택 목록 API와 서버 생성 binding 규칙; 클라이언트가 제출할 값과 보내면 안 되는 값을 구분.
- 만료 입력의 시간대·정밀도, request ID 재사용/중복 클릭 응답, 실제 저장된 Proof ID 및 목록/상세 응답.
- 공개 링크 형식과 기존 QR 생성 의존성/컴포넌트. 새 라이브러리는 담당자 합의 전 추가하지 않습니다.

### W3-A3 · 사용자 조회·비교

- 로그인 없는 Proof-only 조회와 인증된 비교 API의 분리된 경로·입출력 타입.
- `scope`, `verification_status`, `lifecycle_status`, `checks`, `reason_codes` 생성 enum과 필드별 누락/불일치 표현.
- 비교 권한 실패, INCONCLUSIVE/NOT_RUN, RPC unavailable 응답 예시. 공개 조회에서 payload·binding·token이 제외되는 응답 예시.

위 계약·생성 타입을 받으면 해당 입력과 오류 상태를 화면에 연결하고 mock 검사를 실제 API 연결 검사와 분리해 갱신합니다. 승인된 정책의 재논의는 필요하지 않으며, 이 handoff는 정책을 새로 결정하지 않습니다.
