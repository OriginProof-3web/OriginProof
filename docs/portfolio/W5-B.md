# W5 / B / 여하민 — V5-W5-B 1차 체인 증거·이벤트 journal

- `@hamin1228`, 2026-10-16. W5는 개발 단계입니다.
- 브랜치 `codex/v5-w5-b-chain-evidence`, 시작 `a4bfa22bf870f3bd5ae02e439636fbf8204444a7`.
- **B 저수준 독립 구현/합성 검사 완료 / C port adapter·실제 연결·W5 전체 완료는 대기**입니다.

Codex가 B의 생성 ABI 기반 hash-pinned RPC 조회, 직접 제출 calldata/receipt 증거, 승인·정지·버전 이벤트 7종 해석과 배포별 SQLAlchemy journal을 구현했습니다. 이벤트와 cursor의 원자적 저장·재시작·명시 reorg 복구·오래된 projection과 현재 상태 조회 분리를 검사했습니다. 기존 W2~W4 컨트랙트/ABI, httpx·eth-abi·SQLAlchemy·오류 경계를 재사용했습니다. C Draft port는 고정 SHA로 읽기만 했고 사본이나 C/A/D 생산 코드 수정은 없습니다. 사람의 작성·리뷰 승인·기여 비율을 추정하지 않습니다.

최종 Python **229 PASS / 1 live SKIP**에 신규 W5 **50 PASS**가 포함됩니다. 공식 lint·구조·문법·Node hash·생성물 일관성 통과. 외부 Foundry 라이브러리까지 포함한 lint는 기존 외부 코드 26건으로 실패했으며 공식 범위 검사와 구분합니다. 초기 44 PASS 뒤 경계 검사를 6개 추가했습니다. Solidity는 이번 변경이 없어 재검사하지 않았습니다.

실제 새 배포·RPC·직접 제출·API·지갑·PostgreSQL·D 독립 재현은 미실행입니다. 성공 receipt를 C의 CONFIRMED로 취급하지 않습니다. B-C01 고정 승인자 provenance, B-C02 승인 목록/count 대조, B-C03 UNKNOWN 검색/중계·작업별 상태 대조, custom-error 누락 구분과 C 원본 port 변환이 남습니다. **G07은 미해결**입니다. 상세 흐름·명령·한계는 [B 인계](../blockchain/v5_w5_chain_evidence.md)에 기록합니다.

기존 사용자 변경 5개·legacy 경로와 과거 기록을 보존했습니다. 팀 Draft PR·개인 비공개 포트폴리오에 검증한 커밋을 공유하며, 작성자 외 리뷰/실제 연결 완료는 주장하지 않습니다.
