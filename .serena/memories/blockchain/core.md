# Blockchain and Indexer

- B: packages/contracts, services/indexer, apps/api/src/infrastructure/blockchain. Contract와 Adapter는 각각 검증합니다.
- 현재 Registry 구현과 본선 ADR의 Proof lifecycle·single_use 계획을 구분합니다. 체인은 현재 신뢰 상태와 원자적 consume의 최종 권위이며 DB projection은 이를 대체하지 않습니다.
- 원문·개인정보·전체 payload를 온체인에 넣지 않습니다. Registry 운영키와 기관 발행키는 분리합니다.
- 이벤트 projection은 재처리·중복·재시작을 검증합니다. 배포 manifest에 chain ID·주소·source SHA·인자를 남깁니다.
- 권한·상태·경계값과 ABI 호환성을 검사합니다. 표준 Foundry 실행은 deployer 컨테이너를 사용합니다.
