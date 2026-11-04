# OriginProof 본선 시연 서버 — AWS EC2 한 대에 올리기

내 Mac 에서 돌리던 `scripts/rc_local.sh` 환경(DB·Anvil·API·웹 프록시)을 EC2 한 대에 그대로 올리고,
앞에 Caddy 를 두어 HTTPS 주소로 공개합니다. 도메인 없이 `IP.sslip.io` 주소로 인증서가 자동 발급됩니다.

```
심사위원 브라우저 ─ https://3-35-1-2.sslip.io ─▶ Caddy(80·443) ─▶ 웹 프록시 127.0.0.1:8790 ─▶ API 127.0.0.1:18000
                                                                                   └ Postgres(Docker) · Anvil
```
프록시와 API 는 127.0.0.1 에서만 듣습니다. 밖에서는 Caddy 를 거쳐야만 들어옵니다.

---

## 1. AWS 콘솔에서 할 일 (대표님 직접)

1. **예산 알림 먼저**: Billing → Budgets → 월 30달러 알림.
2. **리전**: 오른쪽 위에서 **아시아 태평양(서울) ap-northeast-2**.
3. **EC2 → 인스턴스 시작**
   - 이름 `originproof-demo`
   - OS **Ubuntu Server 24.04 LTS (x86_64)**
   - 유형 **t3.medium** (2 vCPU·4GB, 시간당 약 0.05달러 = 하루 약 1,700원)
   - 키 페어: 새로 만들기 → `originproof-key` → `.pem` 내려받기 → `~/.ssh/` 로 옮기기
   - 네트워크 → 보안 그룹 만들기
     - SSH 22: **내 IP** 만
     - HTTP 80: 위치 무관(0.0.0.0/0)
     - HTTPS 443: 위치 무관(0.0.0.0/0)
   - 스토리지 **30GB** gp3
4. **탄력적 IP**: EC2 → 탄력적 IP → 할당 → 방금 만든 인스턴스에 연결.
   - IP 가 `3.35.1.2` 라면 공개 주소는 **`https://3-35-1-2.sslip.io`** 입니다(점을 하이픈으로 바꿈).

> 쓰지 않을 때는 인스턴스를 **중지**하면 서버 요금이 멈춥니다(디스크·탄력적 IP 요금은 조금 남음). 본선이 끝나면 **종료**하고 탄력적 IP 를 **릴리스**하세요.

## 2. 내 Mac 에서: 코드 보내기 (push 없이)

```bash
chmod 400 ~/.ssh/originproof-key.pem
```

```bash
cd ~/Desktop/2반/OP-키입력삭제 && git bundle create /tmp/op.bundle fix/remove-ai-key-input
```

```bash
scp -i ~/.ssh/originproof-key.pem /tmp/op.bundle ~/Desktop/2반/OP-E2E-실키/scripts/fixtures/wallet_demo_bulk.py ubuntu@3.35.1.2:~
```

```bash
ssh -i ~/.ssh/originproof-key.pem ubuntu@3.35.1.2
```

## 3. 서버에서: 도구 설치 (한 번만, 약 5분)

```bash
sudo apt-get update && sudo apt-get install -y docker.io git curl openssl jq caddy && sudo usermod -aG docker ubuntu
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash - && sudo apt-get install -y nodejs
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -L https://foundry.paradigm.xyz | bash && ~/.foundry/bin/foundryup
exit
```
`exit` 후 다시 `ssh` 로 접속해야 docker 권한과 PATH 가 적용됩니다.

## 4. 서버에서: 코드 풀고 켜기

컨트랙트 의존성(처음 한 번): `./packages/contracts/script/bootstrap_dependencies.sh`

```bash
git clone -b fix/remove-ai-key-input ~/op.bundle ~/OriginProof && cp ~/wallet_demo_bulk.py ~/OriginProof/scripts/fixtures/ && cd ~/OriginProof
```

AI 키는 **서버 터미널에서 대표님이 직접** 붙여 넣습니다(화면에 안 보이고 서버에만 0600 으로 저장).
```bash
scripts/rc_local.sh set-key
```

공개 주소를 넣고 켭니다(`3-35-1-2` 를 실제 IP 로).
```bash
export PUB=https://3-35-1-2.sslip.io
```

```bash
OP5_PUBLIC_ORIGIN=$PUB RC_WEB_PORT=8790 RC_LLM=openai API_LOGINS_PER_MINUTE=120 API_REQUESTS_PER_MINUTE=3000 scripts/rc_local.sh up
```
- `OP5_PUBLIC_ORIGIN`: 웹 프록시가 이 공개 주소의 접속을 받도록 함(이번에 추가한 설정).
- `API_SESSION_COOKIE_SECURE=true` 는 넣지 않음: 서버 안 준비 스크립트가 http 로 로그인해서 시연 데이터 발행이 실패함(브라우저 구간은 Caddy 가 HTTPS 로 감쌈).
- `API_DEMO_ATTACK_USERNAMES`(시연용 공격 재현, 'DB 직접 조작' 단추)는 **넣지 않음**: 넣은 계정이 서버 DB의 시연 안내문 금액을 바꿀 수 있어요. 로컬 노트북(rc_local.sh)에서만 켭니다.
- 분당 제한 상향: 모든 접속이 프록시(127.0.0.1)를 거쳐 API 에는 한 사람처럼 보여서, 기본값(로그인 분당 10번)이면 심사위원 여럿이 동시에 로그인할 때 막힙니다.

## 5. Caddy(HTTPS) 연결

```bash
echo "${PUB#https://} {
  encode gzip
  redir / /entry.html
  reverse_proxy 127.0.0.1:8790
}" | sudo tee /etc/caddy/Caddyfile && sudo systemctl restart caddy
```
1분쯤 뒤 `$PUB/join.html` 이 자물쇠와 함께 열리면 성공입니다.

## 6. 시연 데이터·계정

은행 안내문 10건·관공서 공문 10건:
```bash
export UV_PROJECT_ENVIRONMENT=.uv-venv PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src
```

```bash
. build/rc-local/wallet.env && for o in bank office; do uv run --all-packages --all-groups --frozen python scripts/fixtures/wallet_demo_bulk.py --only $o --api http://127.0.0.1:18000 --rpc-url http://127.0.0.1:18545 --registry "$API_WALLET_REGISTRY_ADDRESS" --manifest packages/contracts/deployments/31337.wallet.local.json --credentials build/rc-local/secrets/test-accounts.json --out build/rc-local/bulk-docs.jsonl --approver1 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 --approver2 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC --institution 0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65 --office 0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc; done
```

운영자 계정 `originproof` (비밀번호는 입력 칸에 직접, 화면에 안 보임). 공개 서버라 `password` 보다 긴 비밀번호를 권합니다.
```bash
read -rs -p '운영자 비밀번호: ' P; echo; UV_PROJECT_ENVIRONMENT=.uv-venv PYTHONPATH=apps/api/src:packages/python API_DATABASE_URL=postgresql+asyncpg://originproof:originproof@127.0.0.1:55433/originproof P="$P" uv run --all-packages --all-groups --frozen python -c 'import asyncio,os,sys; sys.path.insert(0,"scripts/fixtures"); from seed_accounts import create_account; asyncio.run(create_account("originproof","operator",None,os.environ["P"]))'; unset P
```
개인 계정(노랑이 등)은 `$PUB/join.html` 에서 새로 가입합니다(내 Mac 의 DB 는 옮겨지지 않음).

## 7. 확인

```bash
scripts/rc_local.sh status && curl -s $PUB/api/health/ready
```
브라우저에서 `$PUB/join.html` → 가입 → 로그인 → 아래 문장 붙여 넣기 → **✓ 진짜**:
`[오리진 목 은행] 카드 대금 85,000원 청구 안내입니다. 입금계좌 001-234-500003`

## 서버 재부팅·코드 갱신

- 키를 바꾼 뒤: `scripts/rc_local.sh down` 후 다시 `up`(API 가 켜질 때 키를 읽음).
- 재부팅 뒤: 4번의 `export PUB=…` 와 `… scripts/rc_local.sh up` 한 줄만 다시(데이터는 남아 있음, Caddy 는 자동 시작).
- 코드 갱신: Mac 에서 2번(번들·scp) → 서버에서 `cd ~/OriginProof && git pull ~/op.bundle fix/remove-ai-key-input && scripts/rc_local.sh down` 후 다시 `up`.
- 로그: `build/rc-local/logs/` (api.log·web.log), `sudo journalctl -u caddy`.

## 주의

- AI 키·`build/rc-local/secrets/` 는 서버 밖으로 꺼내거나 채팅에 붙여 넣지 않습니다.
- Anvil 은 시연용 체인입니다(실제 자산 없음). 공개 테스트넷(Sepolia)으로 바꾸는 것은 `docs/runbooks/sepolia_deploy.md`.
- OpenAI 사용량: 계정 하나당 10분 5건 분석 제한이 서버에 걸려 있습니다. OpenAI 대시보드에서 월 사용 한도도 걸어 두세요.
