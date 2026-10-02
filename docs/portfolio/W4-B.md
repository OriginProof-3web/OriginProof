# W4 / B / 여하민 — 개인 개발 기록

- GitHub 계정: `@hamin1228`
- 실제 작업일: 2026-10-02 (W4는 달력 주차가 아님)
- 작업 ID: `W4-B1`, `W4-B2`, `W4-B3`
- 준비 브랜치: `codex/w4-b-proof-lifecycle`; `phase/W4` 생성 전 독립 작업
- 시작 기준: `origin/integration@3295a71` → 본인 W3-B 선행 SHA `92e0e94` 반영
- 상태: B 독립 구현·로컬 EVM 검증; C 연결·작성자 외 리뷰·단계 PR 대기

## 수행한 작업

| 작업 | 개인 구현·검증 | 재사용·협업 |
| --- | --- | --- |
| W4-B1 | Proof commitment 등록·폐기·조회, 기관 계정 권한, 반복 폐기 무변경, event/ABI | W1/W2 Issuer/Key Registry, W3-B3 후보와 ADR 재사용 |
| W4-B2 | trusted gateway의 issuer/recipient binding, 현재 기관·키/기간/폐기/소비 검사, 원자적 1회 consume와 경쟁·직접 호출·경계 검사 | C의 서명·세션 검증은 후속 실제 연결 |
| W4-B3 | 새 로컬 배포/manifest, Proof Reader/Writer prepare·receipt·재조회, event decoder/projection, 실제 Anvil 연동 | W2 Writer Operation 복구 계약과 기존 projection 재사용 |

## 주요 판단

- gateway는 서버가 검증한 서명·로그인 결과를 대행하는 권한이다. Contract 자체가
  서명된 JSON이나 웹 세션을 다시 검사한다고 주장하지 않는다.
- 등록 commitment와 Proof owner·binding은 온체인에서 고정하고, 현재 사용 가능 여부는
  Reader가 체인을 다시 읽는다. 이벤트 projection은 이력·재시작용이다.
- `SUBMITTED` hash는 확정이 아니다. canonical 성공 receipt와 최종 상태 재조회 뒤
  `CONFIRMED`를 반환하며 실패/reorg/RPC 단절은 성공으로 바꾸지 않는다.
- phase/W4와 W3-B3 소비 리뷰가 아직 없으므로 W4의 팀 연결·단계 완료를 선언하지 않는다.

## 검증 근거

| 검사 | 실제 결과 |
| --- | --- |
| Foundry 전체 | 21 passed, 0 failed; 신규 Proof 권한·반복·경쟁·기간·binding 포함 |
| Reader/Writer/projection 단위 | 75 passed; 미등록·network·RPC·reorg와 replay 포함 |
| 임시 Anvil 통합 | 1 passed; 새 배포 → 등록 → 상태 재조회 → consume → 실패 receipt → 폐기 → 실제 event projection |
| Python 전체 관련 회귀 | 255 passed, opt-in 4 skipped |
| Ruff·구조·ABI | 변경 Python 형식/정적 검사, 저장소 구조, 생성 ABI와 forge artifact 일치 |

CI·외부 리뷰는 아직 실행/확인하지 않았다. 외부 유료 RPC와 보존 DB 초기화는 실행하지
않았다. 공개 합성 데이터와 매 실행 새 임시 로컬 체인만 사용했다.

## AI 활용과 후속

Codex로 기존 ABI/Writer/Reader·ADR를 추적하고 Contract·Adapter·검사·문서 초안을
작성했다. 권한 분리, 동일 제출의 복구, 현재 체인 조회의 판정 권위와 C 영역 비수정
경계를 확인했다. C는 새 Adapter를 실제 발행·폐기·consume API와 Operation DB에
연결하고, D는 독립 재현을 수행해야 한다.

- 본인 확인: `@hamin1228` / 2026-10-02 / 기록 확인 대기
- 작성자 외 리뷰: 미확인
