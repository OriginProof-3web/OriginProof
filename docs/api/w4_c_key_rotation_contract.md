# W4-C1 — 정상 키 교체와 발행·과거 Proof 연결

- C / @Jordi2801K. 선행 W3 C 작업 PR #35, branch feat/w4-c-key-rotation.
- C 구현·HTTP/DB/서명 및 실제 PostgreSQL·Anvil 확인 완료. A W4-A1 화면·B 소비자 리뷰·D 독립 검증 대기.
- 이 문서는 최초 W4-C1 범위입니다. W4-C2/C3 후속은 [lifecycle 인계](w4_c_proof_lifecycle_contract.md)에 구현·연결 근거를 기록했습니다.

## 호출과 상태

`POST /v1/issuer/keys/rotate`는 자기 활성 기관 issuer 세션·CSRF와 W2 KeyInput을 받습니다.
request_id/reason/valid_from/valid_until을 보내며 새 교체 키는 현재 유효 구간이어야 합니다.
현재 구간 밖의 신규 요청은 422 ROTATION_KEY_NOT_CURRENTLY_VALID입니다.
operation action은 `rotate_key`이며 최초 등록 `register_key`, 유출 폐기 `revoke_key`와 감사 기록을 구분합니다.
동일 action/request_id/입력은 같은 Operation, 변경 입력은 409입니다. 기간이 지나도 기존 요청의 결과를 새 키로 재제출하지 않습니다.

기존 signer 생성·challenge·prepared commit·tx hash commit·receipt 재조회·복구를 그대로 재사용합니다.
새 키 등록이 확정되고 현재 기간/보호된 signer를 확인한 뒤 한 DB transaction으로 선택을 전환합니다.
이전 키는 selected=false로만 바꾸며 정상 교체가 자동 revoke하지 않습니다.
실패/UNKNOWN/DB final 저장 실패 시 기존 선택을 유지합니다. recover는 동일 tx만 확인합니다.
더 최신 등록 nonce의 키가 이미 선택돼 있으면 오래된 작업을 복구해도 최신 선택을 되돌리지 않습니다.

기존 `POST /v1/issuer/keys`의 미래 키 등록은 허용하지만 현재 키를 교체하지 않습니다.
미래 키를 자동 발행 선택으로 승격하는 스케줄러는 없습니다. 즉시 교체에는 현재 유효한 새 키를 rotate로 등록합니다.
오래되거나 기간 종료 뒤 복구된 등록은 CONFIRMED 이력이어도 현재 선택 전환을 뜻하지 않습니다.
A는 Operation 결과 후 `GET /v1/issuer/keys`에서 실제 selected/status를 다시 조회해야 합니다.

## W3 연결과 정책

W3 발행이 같은 PostgreSQL advisory lock으로 선택·실제 기관/키·발행 당시 기간·signer를 재검사합니다.
발행/교체 경쟁 시 한 키의 일관된 서명으로 저장됩니다. 미등록/만료/폐기/secret 오류 키로 새 발행하지 않습니다.
과거 Proof는 서명된 key_id의 실제 signer와 발행 당시 기간을 확인합니다.
정상 교체 및 키 기간 종료만으로 과거 정상 서명을 무효화하지 않습니다.
유출 폐기는 과거 서명이 맞더라도 ISSUER_KEY_REVOKED 원인을 반환합니다.
최초 W4-C1 branch의 ProofStatusRegistry는 NOT_RUN/null이었습니다. W4-C2/C3 후속 branch는 실제 Registry/lifecycle을 연결하며 정상 교체와 유출 폐기의 현재 상태를 분리합니다.

## 검증·인계

- W4 합성 HTTP/SQLite 검사 3 passed: 교체→새 발행→기존 Proof·키 기간 종료/폐기,
  미래 등록/실패 후 선택 보존·경쟁 발행, 오래된 UNKNOWN 복구 후 최신 선택 유지.
- 전체 Python 239 passed / opt-in 5 skipped; Ruff·생성 계약·TypeScript·diff 검사 통과.
- 실제 분리 PostgreSQL 16·Anvil 1.4.4 HTTP 검사 1 passed: 두 유형 발행/비교와
  교체·새 키 발행·과거 서명·미래 등록·실제 비인가 거래 실패·UNKNOWN 늦은 복구·유출 폐기.
- 기존 demo DB/chain·A 화면·B 구현은 수정하지 않았습니다. 실제 브라우저/작성자 외 독립 검증은 미실행입니다.
- W3 PR #35 이후 합치는 W4 추가 PR입니다. W3가 phase/W3에 병합된 뒤 최신 W3 결과를 포함한
  phase/W4로 W4 PR 대상을 변경하고 주차별 연결 검증을 진행합니다.
