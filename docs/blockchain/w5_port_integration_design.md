# W5 B → C WalletRegistry 연결 설계 메모 (미합의 초안)

AI(Codex)가 여하민님 요청으로 #69의 감사 요청을 정리했습니다. 원본은 `packages/python/originproof_core/wallet_ports.py`이고 소비 지점은 C의 `WalletRuntime.rpc` 및 `create_app(wallet_chain=...)`입니다. 공통 DTO·Schema·ABI 복제 없이 원본을 import합니다. **연결 구현·C 합의·실제 API/DB 연결 완료가 아닙니다.** 공개 네트워크도 미검증입니다.

| port 메서드 | B의 변환·증거 책임 | C와 확인할 경계 |
| --- | --- | --- |
| issuer | getIssuer·업무/governance nonce를 같은 canonical snapshot에서 읽어 WalletIssuer로 변환 | 숫자 문자열·상태·기관/키 일치 |
| key | getKey의 등록·retire·compromise block을 WalletKey로 변환 | 미발생 block은 None, 과거 발행 근거 보존 |
| document | version=None이면 같은 snapshot의 latest를 조회하고 getDocument·기관/키 경고·만료를 WalletDocument/DocumentView로 변환 | 저장 상태와 EXPIRED 표시 구분, original_available은 체인만으로 True 금지(C 보관 데이터 결합) |
| proposal | WalletReconciler의 canonical 생성·서로 다른 승인·실행 대조를 WalletProposal로 변환 | status·deadline·nonce와 C 준비 상태를 구분 |
| is_approver | 고정 승인자3명은 검증된 배포/constructor provenance에서만 결정 | 임의 주소 목록이나 DB 역할을 온체인 승인자로 간주 금지 |
| transaction | 실제 calldata를 decode하고 Reconciler로 receipt/event/state를 검증해 WalletTransaction 반환 | Publish/Revoke/Propose/Approve/Suspend 이름 매핑, sender·전체 arguments는 실제 거래에서 취득 |
| submit | 서명/전체 intent와 실제 relayer 경계를 별도 구현 | 기관 개인키 수집 금지, 미구현이면 dependency 오류, 가짜 tx hash 반환 금지 |
| find_transaction | 저장된 전체 intent·actor·deployment부터 bounded Recovery 검색 | C port는 페이지 진행점 필드가 없으므로 DB 보관·범위/예산을 C와 먼저 합의, 완료 페이지의 빈 결과도 재전송 허가 아님 |

## 오류·주입 규칙

1. getter별 정확한 Unknown custom error만 None으로 반환합니다. RPC/ABI/배포 불일치와 getter와 다른 Unknown 오류는 dependency입니다. pending/missing 거래는 None으로 유지하고 CONFIRMED로 바꾸지 않습니다.
2. B의 BlockchainDependencyError는 경계에서 C가 처리하는 `originproof_core.DependencyUnavailableError`로 번역해야 합니다. B 내부 오류를 그대로 C에 흘려 500으로 만들지 않습니다. 모델 validation 실패도 dependency로 처리합니다.
3. ChainPosition은 한 snapshot의 chain/contract/block/hash를 공유하고 reorg 재검사를 통과해야 합니다. C는 WalletRuntime에서 다시 모델/domain/identity와 저장 intent를 검증합니다.
4. 실제 배포 검증을 마친 adapter 인스턴스를 C factory의 `create_app(wallet_chain=adapter)`에 주입하고 HTTP client 수명은 app lifespan과 맞춥니다. 현재 default None의 503 fail-closed를 유지합니다. 운영 설정/수명주기 변경은 C 소유자가 합니다. 이 문서는 실제 adapter 인스턴스를 제공하지 않습니다.
5. C가 저장한 intent의 `action`, `arguments`, 선택 actor를 소비합니다. `WalletTransaction.arguments`에 요청 값을 복사하지 않고 실제 calldata를 반환합니다. 성공/실패 후보가 함께 있으면 첫 실패를 원 요청 실패로 확정하지 않습니다.

## 연결 후 수용 검사

- 정상/미등록/다른 custom error/RPC 단절/잘못된 배포/domain/잘못된 getter 인자.
- 기관·키 사고 경고, 버전별 만료·REVOKED·SUPERSEDED, nonce·권한·v1/v2 consume 회귀 보존.
- C factory에 실제 B adapter를 주입하고 합성 HTTP 단위 검사와 실제 PostgreSQL+Anvil API/Operation 검사를 분리.
- 응답 유실 뒤 API/DB 프로세스 재시작·동시 재조회·원본 검색·중복 제출 방지. 기존 fresh-client Anvil 검사는 제품 Operation 완료 근거가 아님.
- 공개 RPC/finality·relay 내부 호출 trace·provider getLogs chunk는 미검증. G07은 #86 병합 후 D mixed QA가 판정.

C 합의 요청: 위 반환 mapping, constructor 승인자 provenance, find_transaction 페이지 진행점/재시작 보관, submit relayer 수명과 책임. 합의·리뷰를 받은 것으로 기록하지 않습니다.
