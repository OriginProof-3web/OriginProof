# W5 / B / 여하민 — V5-W5-B 1차 체인 증거·이벤트 journal

- `@hamin1228`, 2026-10-16. W5는 개발 단계입니다.
- 브랜치 `codex/v5-w5-b-chain-evidence`, 시작 `a4bfa22bf870f3bd5ae02e439636fbf8204444a7`.
- **B 저수준 독립 구현/합성 검사 완료 / C port adapter·실제 연결·W5 전체 완료는 대기**입니다.

Codex가 B의 생성 ABI 기반 hash-pinned RPC 조회, 직접 제출 calldata/receipt 증거, 승인·정지·버전 이벤트 7종 해석과 배포별 SQLAlchemy journal을 구현했습니다. 이벤트와 cursor의 원자적 저장·재시작·명시 reorg 복구·오래된 projection과 현재 상태 조회 분리를 검사했습니다. 기존 W2~W4 컨트랙트/ABI, httpx·eth-abi·SQLAlchemy·오류 경계를 재사용했습니다. C Draft port는 고정 SHA로 읽기만 했고 사본이나 C/A/D 생산 코드 수정은 없습니다. 사람의 작성·리뷰 승인·기여 비율을 추정하지 않습니다.

최종 Python **229 PASS / 1 live SKIP**에 신규 W5 **50 PASS**가 포함됩니다. 공식 lint·구조·문법·Node hash·생성물 일관성 통과. 외부 Foundry 라이브러리까지 포함한 lint는 기존 외부 코드 26건으로 실패했으며 공식 범위 검사와 구분합니다. 초기 44 PASS 뒤 경계 검사를 6개 추가했습니다. Solidity는 이번 변경이 없어 재검사하지 않았습니다.

실제 새 배포·RPC·직접 제출·API·지갑·PostgreSQL·D 독립 재현은 미실행입니다. 성공 receipt를 C의 CONFIRMED로 취급하지 않습니다. B-C01 고정 승인자 provenance, B-C02 승인 목록/count 대조, B-C03 UNKNOWN 검색/중계·작업별 상태 대조, custom-error 누락 구분과 C 원본 port 변환이 남습니다. **G07은 미해결**입니다. 상세 흐름·명령·한계는 [B 인계](../blockchain/v5_w5_chain_evidence.md)에 기록합니다.

기존 사용자 변경 5개·legacy 경로와 과거 기록을 보존했습니다. 팀 Draft PR·개인 비공개 포트폴리오에 검증한 커밋을 공유하며, 작성자 외 리뷰/실제 연결 완료는 주장하지 않습니다.


## 2026-10-17 · W5 2차 B 대조 로직

`codex/v5-w5-b-reconciliation`에서 자기 1차 `7666bb9bf2d85804b9abe9be5a87ea122e1d914d`를 이어 getter별 정확한 미등록 분류, canonical 승인 목록/count·동일 tx 실행 검증, 전체 intent·이벤트·receipt/현재 상태 대조를 구현했습니다. 발행·철회·제안·승인·정지 5개 경로와 나중 철회/대체/정지/재활성화를 구분합니다. 동일 블록의 정지/재활성화를 분리할 수 없으면 dependency 오류를 반환합니다. 상세 흐름/한계는 [2차 인계](../blockchain/v5_w5_reconciliation.md)입니다.

최종 전체 Python **281 PASS/1 live SKIP**, 2차 신규 52 PASS·1차 50 PASS 포함입니다. 공식 lint·구조·Node hash·생성물 일관성 통과. 최초 37 PASS 뒤 경계 15건을 추가했고 줄길이/변수명 lint 경고를 수정했습니다. Solidity/ABI는 무변경이라 로컬 Foundry를 재실행하지 않았습니다. 원격 CI 결과는 새 Draft PR에서 별도로 확인합니다.

Codex가 B 코드·검사·기록을 작성하고 기존 RPC/ABI·W2~W4 구현·합성 fixture·설치 의존성을 재사용했습니다. 사람의 직접 작성/리뷰·기여 비율을 추정하지 않습니다. 사용자 변경 5개를 보존합니다. C/A/D 생산 코드·공통 계약 변경은 없으며 타 담당 브랜치를 임의 병합하지 않았습니다. 원격 integration `4a9b92d`의 D 추가 반영은 이번 자기 W5 작업 트리 검사에 합산하지 않습니다.

독립 구현·합성 검사 결과이며 W5 단계 전체 완료는 아닙니다. C 원본 port 변환·승인자 배포 provenance·UNKNOWN 검색/중계·최종성/Operation 연결·실제 RPC/DB/지갑·D 리뷰가 남습니다. **G07은 미해결**이며 SG01~16 공유 상태를 바꾸지 않습니다. 팀 Draft PR과 개인 비공개 포트폴리오에 실제 검증한 커밋을 보관합니다.


## 2026-10-17 · W5 3차 실제 RPC·UNKNOWN 검색

`codex/v5-w5-b-live-recovery`에서 자기2차 `6916224`를 이어 전송 없는 bounded 원본 거래 검색·known hash/nonce·checkpoint 재조회를 구현했습니다. 코드 `5a51e4b`, 최종 live 코드 `a064b63f9b44e5f9ccf5a6c9a4f237612d03e0e3`. 실제 새 Anvil에서 Registry 배포·공유 SHA256/EIP-712·공동승인·버전 대체/철회·정지/재활성화·응답 유실/원본 검색·pending/실패·SQLite restart·EVM reorg/rewind·RPC 단절을 검사했습니다. 기존 실행 중인 노드/사용자 배포 파일을 건드리지 않았습니다.

일반 Python306 PASS/2 opt-in SKIP(신규 합성25 포함), 실제 wallet RPC 별도1 PASS. 공식 lint·구조·문법·Node hash·생성물 일관성 통과. 최초 합성1FAIL은 padding을 바꾼 검사 오류, 최초live1FAIL은 수락 즉시 채굴됐다고 가정한 검사 오류였습니다. signature 변경·채굴 대기 분리 뒤 재검증했고, 최종 canonical SHA256 fixture까지 live1 PASS입니다. 성공/실패·pending을 구분하는 제품 기준은 완화하지 않았습니다.

Codex가 B 구현/검사/기록을 작성하고 기존 RPC·Reconciler·Indexer·Registry/ABI 및 C 공통 모델/서명/hash를 재사용했습니다. 사람 리뷰/작성/기여 비율은 미확인입니다. 실제 실행은 종료한 폐기 가능한 합성 체인이고 API/C port·Operation/DB·브라우저·PostgreSQL·G07·공개 체인·D 독립 QA는 미완료입니다. 빈 검색은 재전송 허가가 아닙니다. [3차 인계](../blockchain/v5_w5_live_recovery.md)와 [실행 증거](../blockchain/evidence/v5_w5_live_a064b63.json)에 코드 SHA·manifest/receipt·실패/한계를 기록합니다. 기존 사용자5개 변경을 보존하며 W5 전체/SG01~16을 완료 처리하지 않습니다.
