# 이전 독립 PR 검사 기록 — 2026-10-02 17:24

이 문서는 초기 PR #35/#40 독립 검사 기록입니다. 이후 실제 웹·PostgreSQL·Anvil 연결 및 최신 실행 방법은 [웹 연결 검사 기록](WEB_CONNECTION_TESTS.md)을 따릅니다. 아래 미실행과 디자인 인증 설명은 당시의 상태이며 최신 연결 상태가 아닙니다.


## 검사 대상과 환경

- C PR #35: https://github.com/OriginProof-3web/OriginProof/pull/35
  - SHA `17c24a36a46c6b2a823a3b7fac20c97c6faee98f`
  - `make test-api`: 26 passed / 4 skipped.
- B PR #40: https://github.com/OriginProof-3web/OriginProof/pull/40
  - SHA `92e0e94cba8e7799f709060afc9f4e02d220d142`
  - `PYTHONPATH=apps/api/src:packages/python:services/analyzer/src UV_PROJECT_ENVIRONMENT=.uv-venv uv run pytest -q services/indexer/tests`: 78 passed / 1 skipped.
- macOS / Python 3.13.15 / pytest 8.4.2 / 각 PR uv.lock으로 `uv sync --frozen --all-packages --all-groups`.
- GitHub의 고정 SHA 아카이브를 임시 디렉터리에서 각각 실행. 다른 팀원 branch checkout/merge/cherry-pick 없음. 기존 저장소 main과 개인 .env 변경 없음.
- 관리자 재실행은 동일 pytest 범위를 `--junitxml`로 실행하며 실제 개별 결과·실행 시각·명령·출력을 collaboration-results.json에 기록합니다.

## 실제 확인 범위

- C: 두 유형 발행·실제 서명·SQLite 저장·동일 요청 동시 재시도, 기관 목록 분리, 지정 수신자 조회, 정상/금액·문서번호 변조/부분 비교, 권한 거부, RPC 실패, 저장 rollback, signer/기간/배포 불일치. W1 인증·신청 및 W2 Operation 회귀 포함.
- B: 동일 블록 snapshot·reorg/RPC/network 실패 처리, v2 canonical digest·signer·chain/domain/schema/proof type 경계, 기존 Writer/Reader/projection 회귀.
- 위 항목은 팀원이 작성한 테스트의 실행·재현입니다. 새 독립 수용 사례를 작성하거나 팀원의 코드 리뷰를 승인한 결과가 아닙니다.
- 브라우저: 잘못된 테스트 비밀번호의 이동 거부, 올바른 입력의 관리자 이동, PR별 결과 표시, B 검사 재실행 버튼과 완료 복귀를 확인했습니다. 이는 로컬 디자인 동선 검사이며 서버 관리자 인증 검증이 아닙니다.

## 미실행과 연결 대기

- Docker daemon 미기동, disposable PostgreSQL/Anvil 및 TEST_DATABASE_URL/TEST_CHAIN_* 미설정으로 C live 4개와 B local EVM 1개 미실행.
- Foundry 컨테이너 검사 미실행. Python의 digest 검사는 Solidity 실행을 대신하지 않습니다.
- 사용자/기업 화면의 실제 API 연결, 두 역할의 브라우저 발행→조회→변조 비교 E2E, LAN/QR 검증 미실행.
- C SHA의 finals_proofs.py는 get_issuer/get_key를 분리 호출합니다(240·444·445행). B #40의 get_issuer_key_snapshot 연결은 C 담당 후속 작업입니다. 두 PR을 합쳐 테스트하지 않았습니다.
- ProofStatusRegistry·폐기·consume 실구현 검증은 W4 범위. W3 proof_status NOT_RUN / lifecycle null이며 현재 사용 가능 또는 단계 완료를 선언하지 않습니다.
- PR #35/#40 작성자 외 리뷰 및 D 독립 검증 대기.
- DB 초기화·운영 배포·유료 호출·외부 PR 댓글/메시지 전송 없음.

## 관리자에서 실행

`협업 테스트 시작.command`를 더블클릭하면 로컬 서버를 시작하고 관리자 페이지를 엽니다. 실행 중인 서버가 있으면 재사용합니다. 서버를 시작한 터미널에서 Control+C를 누르면 서버가 종료됩니다.

```sh
cd '/Users/khj/Desktop/해커톤/해커톤 본선/웹 디자인'
python3 collaboration-server.py
```

http://127.0.0.1:8768/user-login.html 에서 기존 테스트 아이디로 관리자 페이지 진입.
실행 버튼은 고정된 두 PR 검사만 실행합니다. 임시 복사본에서 수행하며 개인 .env와 live DB/chain 환경변수를 사용하지 않습니다.
첫 실행에는 gh 인증·uv·네트워크가 필요합니다. 준비된 고정 SHA는 임시 캐시를 재사용합니다. 서버는 로컬 127.0.0.1에만 바인딩합니다.
단순 file:// 화면 열기로는 Python 검사를 실행할 수 없습니다.
