# W2 / B / 여하민 — V5-W2-B 공동승인·키 증명·정지

- GitHub 계정: `@hamin1228`; 작업일: 2026-10-16 (W2는 개발 단계).
- 상태: Contract 독립 구현·검사 완료 / 실제 배포·Adapter·C/A/D 연결·작성자 외 리뷰 대기.
- 작업: V5-W2-B; 브랜치 `codex/v5-w2-b-governance`.
- 시작 SHA: `c2111e379889d8550aa6ff893d44f576fb78189a` (자기 W1 결과 보존).
- 구현 SHA: `fa333c699d33a223b0d00d97ea353a29fe058f75`.
- 검증 코드 SHA: `0f240dbd2ee42c059e26e4bdbb3d0dc843858fd7`; 이후 기록 커밋은 문서만 변경.
- PR/원격 CI: 미생성·미실행. 원격 push 미실행. 과거 phase를 보존하고 새 단계 대상은 C와 조율 예정.

## 문제와 실제 결과

준비 ABI/Golden만 있던 W2 기관 권한 경로에 고정 승인자 3명 중 2명 승인, EIP-712 키 보유 증명, 기관별 governance nonce, 단독 긴급 정지, 키 교체/사고 이력, 공동 재활성화를 구현했습니다. 발행/철회 함수는 아직 제공하지 않으며 전체 Registry/API 연결 완료가 아닙니다.

## 개인 기여·재사용·판단

Codex가 B의 컨트랙트·컴파일 ABI·검사와 이 기록/기존 인계의 B 절을 작성했습니다. C API/모델·A 웹·D 분석기는 수정하지 않았습니다. 사람의 직접 작성·코드 승인·기여 비율은 대신 주장하지 않습니다.

공유 인터페이스의 구조·이벤트/준비 서명 계약, C의 Python Golden, 기존 Registry 회귀, OpenZeppelin EIP712/ECDSA/SafeCast와 Foundry를 재사용했습니다. 새 의존성·공유 ABI 변경 없이 W2 부분만 구현하고 신규 함수를 성공 stub으로 만들지 않았습니다. 같은 기관의 과거 signer를 새 keyId로 재활성화하는 우회를 막고 키 이력은 보존했습니다. 과거 서버 기관키/gateway/consume을 신규 권한으로 가져오지 않았습니다.

[과거 W2-B 기록](https://github.com/OriginProof-3web/OriginProof/blob/3ef1fd40943914c1450e8bc05047119ab7eabbc0/docs/portfolio/W2-B.md)은 고정 SHA로 보존합니다. 그 기록의 검사·승인·기여를 이번 v5 성과로 합산하거나 덮어쓰지 않았습니다.

## 검증과 실제 범위

Foundry offline **48 PASS**(기존 21 + 신규 W2 27), Python 공유 계약 **24 PASS**, Node hash·ABI/생성물 대조·변경 파일 format·링크/diff 검사 통과. 상세 명령·검사별 의미·ABI 재생성·소비자 경계는 [기존 인계 4.2절](../handoffs/v5_reuse_handoff.md#42-v5-w2-b-공동승인키-증명정지-독립-구현-2026-10-16)을 기준으로 사용합니다.

macOS arm64, solc 0.8.26, Python 3.13.14, Foundry 내부 EVM·합성 키/fixture 기준입니다. 실제 RPC/DB/지갑/공개 네트워크 검사가 아닙니다. 신규 Golden 교차 검사는 고정 fixture 주소에 runtime을 etch해 원본 Python 서명을 소비했으며 실제 주소에 배포한 것으로 표현하지 않습니다. 성능·가스 운영 비용은 미측정입니다.

## 남은 작업·사실 확인

B-C01 승인자 배포 근거, B-C02 canonical 이벤트/승인 목록, B-C03 UNKNOWN/배포 식별과 실제 Adapter가 남습니다. 신규 발행·업무 nonce·버전·철회는 W3/W4 후속입니다. 기존 v1/v2·consume의 원본/회귀는 보존하되 전체 재실행은 이번 범위 밖입니다. G07과 실제 연결·독립 검증은 미해결입니다. W2 단계 전체 완료를 주장하지 않습니다.

- 본인 기여/계약 확인: 미확인.
- C/A/D 소비 리뷰·작성자 외 리뷰: 미확인.
- 사람의 판단: 사용자가 선택한 기존 ABI 유지·B 범위 W2 구현 방식을 반영했으며 코드의 사람 검토는 대기.
