# W6 RC 개인 재현 안내 (팀원 각자 1회)

작성 2026-10-31 · C 강민서 @Jordi2801K. AI(Codex, claude-opus-5-5)가 사용자님 지시로 작성하고, 새 clone에서 이 순서 그대로 실행해 확인했습니다.

**목적:** 팀원 모두가 자기 노트북에서 같은 RC를 새로 받아 **30~60분 안에** 설치·자동 검사·핵심 화면 동선을 한 번씩 확인합니다. 장비마다 다른 설치·실행 문제를 동결 전에 찾고, 발표 당일 누구든 대신 띄울 수 있게 하는 것이 목표입니다. 발표 장비에서 하는 전체 리허설 3회는 장비가 정해진 뒤 [다른 장비 재현 및 최종 리허설 안내](../qa/other-device-reproduction-and-rehearsal.md)를 따릅니다.

**기준 버전:** #110에 공지하는 최종 RC의 40자리 SHA입니다. 공지 전에는 `phase/W6` 최신으로 미리 연습해도 되고, 결과에 실제로 쓴 SHA를 적어 주세요.

## 0. 준비물

| 도구 | 기준 | 확인 명령 |
| --- | --- | --- |
| Git | 저장소 접근 | `git --version` |
| Docker | **실행 중**이어야 함 | `docker info` |
| uv | 0.8.17 이상 | `uv --version` |
| Node.js | 22 | `node --version` |
| Foundry | 1.4.4 (`anvil`·`forge`·`cast`) | `forge --version` |
| curl, openssl | 기본 설치 | — |

Windows는 WSL2(Ubuntu)와 Docker의 WSL 연동을 켜고, 아래 명령을 모두 WSL 터미널에서 실행합니다. Python은 uv가 알아서 받습니다.

## 1. 새 폴더에 받기

기존 작업 폴더를 쓰지 않고 새로 받습니다.

```bash
git clone https://github.com/OriginProof-3web/OriginProof.git OriginProof-rc-check
cd OriginProof-rc-check
git switch --detach <공지된 RC SHA>     # 공지 전 연습: git switch --detach origin/phase/W6
git rev-parse HEAD                      # 결과에 적을 SHA
```

## 2. 설치와 자동 검사 (약 10분)

```bash
export UV_PROJECT_ENVIRONMENT=.uv-venv
uv sync --all-packages --all-groups --locked
FOUNDRY_BIN_DIR="$(dirname "$(command -v forge)")" make bootstrap-contracts
make test
forge test --root packages/contracts --offline
node --test apps/web-v5/시험/*.test.js apps/web-v5/시험/*.test.mjs apps/web-v5/시험/가져온/*.test.js apps/web-v5/시험/가져온/regression/*.test.js
```

| 검사 | 통과 기준 | 참고: `phase/W6` `f1d7b3c`에서 C가 실행한 값 |
| --- | --- | --- |
| `make test` | failed·error 0 | 1425 passed, 19 skipped |
| `forge test` | failed 0 | 101 passed |
| 웹 `node --test` | fail 0 | 126 pass, 6 skipped |

숫자는 RC에 따라 조금 달라질 수 있습니다. 출력된 숫자를 그대로 적어 주세요. `make test`는 127.0.0.1 포트를 여는 시험이 있어 방화벽 허용 창이 뜨면 허용합니다.

## 3. 서비스 띄우기 (처음 1~3분)

```bash
scripts/rc_local.sh up
```

이 명령 하나로 아래가 준비됩니다. 처음 한 번만 배포·계정·시연 데이터를 만들고, 다음부터는 서비스만 다시 켭니다.

- 합성 DB 컨테이너 `originproof-rc-postgres`(127.0.0.1:55433). 기존 Docker 컨테이너·볼륨은 건드리지 않습니다.
- 로컬 체인 Anvil(18545)과 지갑 Registry 배포. 승인자 3명과 기관 지갑은 Anvil 공개 시험 계정입니다.
- API(18000)와 웹 프록시(8790). 텍스트·사진 입력, 합성 가입, 데모 메일을 켭니다.
- 합성 계정, 그리고 기관 신청 → 2-of-3 승인 → 안내문 v1(154,000원)·v2(120,000원) 발행 → 검증
- 화면에 붙여 넣을 검증 문장 `build/rc-local/verify-samples.txt`

개인 `.env`는 고치지 않습니다. AI는 `LLM_PROVIDER=mock`(규칙 검사만)으로 강제해 **유료 호출이 없습니다**. 실제 AI 모드(`set-key`, `RC_LLM=openai`)는 팀이 정한 담당자만 씁니다. 개인 재현에서는 쓰지 않습니다. 포트가 이미 쓰이고 있으면 `RC_PG_PORT`·`RC_RPC_PORT`·`RC_API_PORT`·`RC_WEB_PORT`로 바꿉니다(예: `RC_API_PORT=18100 scripts/rc_local.sh up`). 웹 포트를 바꾸면 아래 주소의 8790도 같이 바꿉니다.

끝에 아래처럼 나오면 성공입니다.

```text
• 검증 [정본 v2] → VERIFIED · 상태 ACTIVE
• 검증 [금액 1원 변조] → TAMPERED · 상태 ACTIVE PROTECTED_FIELDS_MISMATCH
• 검증 [정정 전 v1] → VERIFIED · 상태 SUPERSEDED
DB      running
Anvil   31337
API     live 200 · ready 200
웹      200  http://127.0.0.1:8790/business.html?mode=api
```

## 4. 화면 확인 (핵심 5개, 약 15분)

브라우저(Chrome 권장)에서 **http://127.0.0.1:8790/business.html?mode=api** 를 엽니다. `localhost`가 아니라 `127.0.0.1`로 엽니다.

| # | 하는 일 | 기대 결과 |
| --- | --- | --- |
| R1 | 왼쪽 `기관 상태` → `로그인 화면 열기` → 계정 `v5_bank`, 비밀번호는 `build/rc-local/secrets/test-accounts.json`의 `password` 값 → 다시 `기관 상태` → `실서버 모드로 바꾸기` | 로그인 구역 "v5_bank · 역할 issuer · 기관 iss_origin_mock_bank", ready "(HTTP 200)", "실서버 모드로 바꿨어요." |
| R2 | 입력칸에 `[국민건강보험] 고객님 환급금 154,000원이 미지급 상태입니다. 아래 링크에서 원격지원 앱을 설치하고 본인 계좌 비밀번호를 입력해 주세요. http://refund-nhis.example.invalid` → Enter | AI 칸 "위험 신호", 근거 "비밀번호를 입력해 주세요" · `CREDENTIAL_REQUEST`, 보관 줄 `상태 COMPLETED` |
| R3 | `verify-samples.txt`의 **J1** 줄(`{`부터) 붙여 넣기 → Enter | 종합 "발행 기록 확인", 공식 발행 "확인됨" · 원본 일치 "일치" · 현재 상태 "유효" |
| R4 | **J2**(금액 1원 변조) | 종합 "원본과 다름", 원본 일치 "불일치" |
| R5 | **J3**(정정 전 v1) | 종합 "새 버전 있음", 현재 상태 "새 버전 있음" |

여유가 있으면 J4(문서 ID만 → "판단 보류"), J5(없는 문서 → "기록 없음"), 개인 회원 `rc-viewer@example.invalid`(비밀번호 같음) 로그인도 확인합니다. 알려진 한계(K1~K10)는 #110의 C 코멘트(10-30)에 정리돼 있습니다. 그중 **실서버 모드에서 시연 버튼 `정상 안내문`은 "기록 없음"이 나오는 것이 현재 알려진 문제(K1)**라 실패로 세지 않습니다.

## 5. 결과 알려 주기

#110에 아래 양식으로 코멘트를 남깁니다. 비밀번호·키·토큰은 적지 않습니다.

```text
[개인 재현] 이름 / 날짜
장비·OS·CPU: (예: MacBook Air M2 / macOS 15, Windows 11 + WSL2 Ubuntu 24.04)
RC SHA: (git rev-parse HEAD)
도구: uv / node / docker / forge 버전
2단계 자동 검사: make test (passed/skipped), forge (passed), web (pass/skip)
3단계 up: 성공 / 실패(마지막 오류 줄)
4단계 화면: R1 R2 R3 R4 R5 각각 통과/실패
막힌 곳·고친 방법:
```

## 6. 끄기와 정리

```bash
scripts/rc_local.sh status   # 상태 보기
scripts/rc_local.sh down     # 끄기(데이터 유지, 다음 up에서 그대로)
scripts/rc_local.sh purge    # 재현 환경 전부 삭제(build/rc-local, 컨테이너, 로컬 배포 기록)
```

`purge`는 이 스크립트가 만든 `originproof-rc-postgres` 컨테이너와 `build/rc-local/`만 지웁니다. 터미널을 닫아도 서비스가 계속 켜져 있으니 끝나면 `down`을 실행해 주세요.

## 7. 막혔을 때

| 증상 | 해결 |
| --- | --- |
| `docker` 관련 오류 | Docker Desktop(또는 WSL Docker)을 켜고 `docker info` 확인 |
| `forge build 실패` | 2단계의 `make bootstrap-contracts`를 먼저 실행 |
| 포트 사용 중 | 3단계의 `RC_*_PORT` 환경 변수로 포트 변경 |
| `up` 중간에 실패 | `build/rc-local/logs/`의 마지막 로그 확인 → `scripts/rc_local.sh purge` 뒤 다시 `up` |
| 화면에 "예시 모드" 칩 | 로그인 뒤 `기관 상태` → `실서버 모드로 바꾸기` |
| 로그인 뒤 분석이 "로그인이 필요해요" | 주소를 `127.0.0.1`로 열었는지 확인(`localhost`와 쿠키가 다름) |
