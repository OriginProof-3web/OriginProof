#!/usr/bin/env bash
# W6 RC 개인 재현용 로컬 실행: 합성 DB(Docker)·Anvil·Registry·API·웹 프록시를 띄우고 시연 데이터를 넣는다.
# 사용: scripts/rc_local.sh up | status | down | purge | set-key | clear-key
# 개인 .env는 읽기만 될 뿐 고치지 않고, 설정은 아래 환경 변수로 넘긴다(환경 변수가 .env보다 우선).
# 포트는 RC_PG_PORT·RC_RPC_PORT·RC_API_PORT·RC_WEB_PORT로 바꿀 수 있다.
# 기본 AI는 mock(유료 호출 없음). 실제 AI는 팀이 정한 사람만: set-key 로 키를 넣고 RC_LLM=openai ... up
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

RUN="$PWD/build/rc-local"
PG_NAME=${RC_PG_NAME:-originproof-rc-postgres}
PG_PORT=${RC_PG_PORT:-55433}
RPC_PORT=${RC_RPC_PORT:-18545}
API_PORT=${RC_API_PORT:-18000}
WEB_PORT=${RC_WEB_PORT:-8790}
RPC="http://127.0.0.1:$RPC_PORT"
API="http://127.0.0.1:$API_PORT"
MANIFEST="$PWD/packages/contracts/deployments/31337.wallet.local.json"
KEY_FILE="$RUN/secrets/openai.key"
# 실서버 모드 시연 버튼(op5_presets.js)이 읽는 문서 JSON. ID·기한이 RC마다 달라 Git에 넣지 않는다.
PRESET_FILE="$PWD/apps/web-v5/페이지/data/rc_presets.json"
# Anvil 기본 공개 시험 계정(실제 자산 없음): 0 배포, 1~3 승인자, 4 합성 기관(은행) 지갑, 5 합성 오피스 지갑
DEPLOYER=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
APPROVER1=0x70997970C51812dc3A010C7d01b50e0d17dc79C8
APPROVER2=0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
APPROVER3=0x90F79bf6EB2c4f870365E785982E1f101E93b906
INSTITUTION=0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65
OFFICE=0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc

export UV_PROJECT_ENVIRONMENT=.uv-venv
export PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src
UVR=(uv run --all-packages --all-groups --frozen)

say() { printf '• %s\n' "$*"; }
die() { printf '✕ %s\n' "$*" >&2; exit 1; }
alive() { [ -f "$RUN/$1.pid" ] && kill -0 "$(cat "$RUN/$1.pid")" 2>/dev/null; }
wait_for() { for _ in $(seq 1 60); do eval "$1" >/dev/null 2>&1 && return 0; sleep 1; done; die "$2"; }

llm_env() {
  if [ "${RC_LLM:-mock}" = openai ]; then
    [ -s "$KEY_FILE" ] || die "키 파일이 없어요: scripts/rc_local.sh set-key 로 먼저 넣으세요"
    OPENAI_API_KEY="$(cat "$KEY_FILE")"; export OPENAI_API_KEY LLM_PROVIDER=openai
  else
    export LLM_PROVIDER=mock OPENAI_API_KEY=
  fi
}

api_env() {
  export API_DATABASE_URL="postgresql+asyncpg://originproof:originproof@127.0.0.1:$PG_PORT/originproof"
  export CHAIN_TARGET=anvil API_BLOCKCHAIN_RPC_URL="$RPC" API_WALLET_MANIFEST_PATH="$MANIFEST"
  export API_SIGNER_DIRECTORY="$RUN/secrets" API_PROJECTION_ENABLED=true
  export API_WALLET_DEMO_EMAIL_ENABLED=true API_WALLET_TEXT_INPUT_ENABLED=true
  export API_WALLET_IMAGE_INPUT_ENABLED=true API_SIGNUP_ENABLED=true API_WALLET_RELAY_ENABLED=false
  # 실제 AI 확인용 합성 계정만 10분 5건 제한에서 뺀다(#116 이후 적용, 그 전 서버는 이 값을 무시).
  export API_ANALYSIS_LIMIT_EXEMPT_USERNAMES='["rc-ai-tester@example.invalid"]'
  [ -f "$RUN/secrets/email-secret" ] || (umask 077; openssl rand -base64 32 > "$RUN/secrets/email-secret")
  API_WALLET_EMAIL_SECRET="$(cat "$RUN/secrets/email-secret")"; export API_WALLET_EMAIL_SECRET
  # shellcheck disable=SC1091
  [ -f "$RUN/wallet.env" ] && . "$RUN/wallet.env"
  return 0
}

start_db() {
  if docker inspect "$PG_NAME" >/dev/null 2>&1; then docker start "$PG_NAME" >/dev/null
  else docker run -d --name "$PG_NAME" -e POSTGRES_DB=originproof -e POSTGRES_USER=originproof \
      -e POSTGRES_PASSWORD=originproof -p "127.0.0.1:$PG_PORT:5432" postgres:16.4-alpine >/dev/null; fi
  wait_for "docker exec $PG_NAME pg_isready -h 127.0.0.1 -U originproof -d originproof" "DB가 준비되지 않았어요"
}

start_chain() {
  # 재기동 뒤에도 배포 블록의 과거 상태가 있어야 Registry 배포 확인(CREATE·코드)이 통과한다.
  alive anvil && return 0
  nohup anvil --host 127.0.0.1 --port "$RPC_PORT" --chain-id 31337 --state "$RUN/anvil-state.json" \
    --preserve-historical-states \
    > "$RUN/logs/anvil.log" 2>&1 & echo $! > "$RUN/anvil.pid"
  wait_for "cast chain-id --rpc-url $RPC" "Anvil이 켜지지 않았어요(logs/anvil.log)"
}

start_api() {
  # 실행 중인 API의 AI 모드가 이번 요청과 다르면 API만 다시 켠다.
  if alive api && [ "$(cat "$RUN/api.mode" 2>/dev/null)" != "$LLM_PROVIDER" ]; then
    kill "$(cat "$RUN/api.pid")"; rm -f "$RUN/api.pid"; sleep 2
  fi
  alive api || { nohup "${UVR[@]}" uvicorn originproof_api.main:app --host 127.0.0.1 --port "$API_PORT" \
    --workers 1 --no-proxy-headers > "$RUN/logs/api.log" 2>&1 & echo $! > "$RUN/api.pid"; \
    echo "$LLM_PROVIDER" > "$RUN/api.mode"; }
  wait_for "curl -sf $API/health/live" "API가 켜지지 않았어요(logs/api.log)"
  # node를 셸로 감싸지 않아야 $!가 node 자신이고 down이 끌 수 있다(프록시는 cwd와 무관).
  alive web || { OP5_PROXY_PORT="$WEB_PORT" OP5_UPSTREAM="$API" \
    nohup node apps/web-v5/개발/op5-proxy.mjs > "$RUN/logs/web.log" 2>&1 & echo $! > "$RUN/web.pid"; }
  wait_for "curl -sf http://127.0.0.1:$WEB_PORT/business.html" "웹 프록시가 켜지지 않았어요(logs/web.log)"
}

first_setup() {
  say "Registry 배포(로컬 Anvil)"
  (cd packages/contracts && forge build > "$RUN/logs/forge-build.log" 2>&1) \
    || die "forge build 실패(logs/forge-build.log): make bootstrap-contracts 를 먼저 실행하세요"
  CHAIN_RPC_URL="$RPC" WALLET_APPROVER_1_ADDRESS=$APPROVER1 WALLET_APPROVER_2_ADDRESS=$APPROVER2 \
    WALLET_APPROVER_3_ADDRESS=$APPROVER3 "${UVR[@]}" python packages/contracts/script/deploy_wallet_registry.py \
    --chain-target anvil --unlocked --sender $DEPLOYER --source-commit-sha "$(git rev-parse HEAD)" \
    > "$RUN/logs/deploy.log" 2>&1 || die "Registry 배포 실패(logs/deploy.log)"
  REGISTRY=$("${UVR[@]}" python -c "import json;print(json.load(open('$MANIFEST'))['contracts']['OriginProofWalletRegistry']['address'])")
  echo "export API_WALLET_REGISTRY_ADDRESS=$REGISTRY" > "$RUN/wallet.env"
  say "DB migration·합성 계정"
  api_env
  "${UVR[@]}" alembic -c apps/api/alembic.ini upgrade head > "$RUN/logs/migrate.log" 2>&1 || die "migration 실패(logs/migrate.log)"
  "${UVR[@]}" python scripts/fixtures/seed_accounts.py --v5-wallet > "$RUN/logs/seed.log" 2>&1 || die "계정 준비 실패(logs/seed.log)"
  grep '^API_WALLET_INTERNAL_APPROVERS=' "$RUN/logs/seed.log" | sed "s/^/export /; s/=\(.*\)$/='\1'/" >> "$RUN/wallet.env"
  grep '^API_WALLET_OPERATOR_ADDRESSES=' "$RUN/logs/seed.log" | sed "s/<approver1 wallet address>/$APPROVER1/; s/<approver2 wallet address>/$APPROVER2/; s/<approver3 wallet address>/$APPROVER3/; s/^/export /; s/=\(.*\)$/='\1'/" >> "$RUN/wallet.env"
  api_env
  start_api
  say "시연 데이터: 기관 신청 → 2-of-3 승인 → 안내문 v1·v2 발행 → 검증"
  "${UVR[@]}" python scripts/fixtures/wallet_demo_flow.py --chain-target anvil --api "$API" --rpc-url "$RPC" \
    --registry "$API_WALLET_REGISTRY_ADDRESS" --manifest "$MANIFEST" --credentials "$RUN/secrets/test-accounts.json" \
    --signer rpc --approver1 $APPROVER1 --approver2 $APPROVER2 --institution $INSTITUTION | tee "$RUN/logs/demo.log"
  ensure_accounts
  write_bulk
  write_samples
}

# /health/ready는 recipient 계정도 있어야 200이라 개인 계정을 만들고, 실제 AI 확인용 계정도 만든다.
# 면제 계정 이름은 가입 API가 거절하므로(#116) 운영자 경로(seed_accounts)로 DB에 직접 만든다.
ensure_accounts() {
  "${UVR[@]}" python - "$RUN" <<'PY'
import asyncio, json, sys
sys.path.insert(0, "scripts/fixtures")
from seed_accounts import create_account
password = json.load(open(f"{sys.argv[1]}/secrets/test-accounts.json"))["password"]
for name in ("rc-viewer@example.invalid", "rc-ai-tester@example.invalid"):
    try:
        asyncio.run(create_account(name, "recipient", None, password))
    except SystemExit:
        pass  # already there
PY
}

write_samples() {
  docker exec "$PG_NAME" psql -U originproof -d originproof -At -c \
    "select json_build_object('document_id',document_id,'version',version,'protected_fields',content) from wallet_document_versions order by version" \
    > "$RUN/docs.jsonl"
  "${UVR[@]}" python - "$RUN" "$PRESET_FILE" <<'PY'
import json, sys
run = sys.argv[1]
docs = [json.loads(line) for line in open(f"{run}/docs.jsonl") if line.strip()]
# 정정된 시드 안내문(v2)과 그 v1. 시연 문자 원본(write_bulk, 모두 v1)이 섞여도 같은 문서의 두 판을 고른다.
v2 = max(docs, key=lambda d: d["version"])
v1 = next(d for d in docs if d["document_id"] == v2["document_id"] and d["version"] == 1)
tampered = dict(v2, protected_fields=dict(v2["protected_fields"], amount_minor=v2["protected_fields"]["amount_minor"] + 1))
unknown = dict(v2, document_id="0x" + "ab" * 32)
lines = [("J1 정본 v2", v2), ("J2 금액 1원 변조", tampered), ("J3 정정 전 v1", v1),
         ("J4 문서 ID만", {"document_id": v2["document_id"], "version": v2["version"]}), ("J5 없는 문서", unknown)]
with open(f"{run}/verify-samples.txt", "w", encoding="utf-8") as out:
    for label, body in lines:
        out.write(f"# {label}\n{json.dumps(body, ensure_ascii=False, separators=(',', ':'))}\n\n")
with open(sys.argv[2], "w", encoding="utf-8") as out:
    presets = {"genuine": v2, "tamper": tampered, "superseded": v1}
    # DB 직접 조작 장면의 대상: 시연 문자 원본의 은행 #10(430,000원). 원래 값은 DB가 아니라 발행 때 남긴 기록에서(조작 중에 다시 만들어도 원래 값)
    try:
        bulk = [json.loads(line) for line in open(f"{run}/bulk-docs.jsonl") if line.strip()]
        target = next(d for d in bulk if d["content"].get("payee_account_number") == "001234500010")
        presets["db_target"] = {"document_id": target["document_id"], "version": target["version"], "protected_fields": target["content"]}
    except (OSError, StopIteration):
        pass
    json.dump(presets, out, ensure_ascii=False)
PY
}

# 시연 문자 모음(apps/web-v5/개발/시연_문자_모음.md)의 원본: 은행 납부 안내 10건·오피스 공문 10건.
# 두 번 발행하면 같은 금액·계좌 기록이 2건이 되어 원본 찾기가 '여러 개'가 되므로 한 번만 발행한다.
write_bulk() {
  [ -s "$RUN/bulk-docs.jsonl" ] && return 0
  [ -e "$RUN/bulk-docs.jsonl.part" ] && die "시연 문자 원본 발행이 전에 중간에 멈췄어요(logs/bulk.log). 중복을 막으려고 다시 발행하지 않아요: scripts/rc_local.sh purge 후 up"
  say "시연 문자 원본: 은행 납부 안내 10건·오피스 공문 10건 발행(1~2분)"
  "${UVR[@]}" python scripts/fixtures/wallet_demo_bulk.py --api "$API" --rpc-url "$RPC" \
    --registry "$API_WALLET_REGISTRY_ADDRESS" --manifest "$MANIFEST" --credentials "$RUN/secrets/test-accounts.json" \
    --out "$RUN/bulk-docs.jsonl.part" --approver1 $APPROVER1 --approver2 $APPROVER2 \
    --institution $INSTITUTION --office $OFFICE > "$RUN/logs/bulk.log" 2>&1 || die "시연 문자 원본 발행 실패(logs/bulk.log)"
  mv "$RUN/bulk-docs.jsonl.part" "$RUN/bulk-docs.jsonl"
}

# DB 직접 조작 시연: 서버 DB에 저장된 은행 #10 안내문의 금액만 몰래 바꾼다(체인·서명은 그대로). 시연 단추 'DB 직접 조작'으로 확인하면 변조로 잡힌다.
DB_TARGET_ACCOUNT=001234500010
db_amount() {
  docker exec "$PG_NAME" psql -U originproof -d originproof -At -c \
    "update wallet_document_versions set content = jsonb_set(content::jsonb, '{amount_minor}', '$1')::json where content->>'payee_account_number' = '$DB_TARGET_ACCOUNT' returning content->>'amount_minor'" \
    | head -1
}

status() {
  printf 'DB      %s\n' "$(docker inspect -f '{{.State.Status}}' "$PG_NAME" 2>/dev/null || echo 없음)"
  printf 'Anvil   %s\n' "$(cast chain-id --rpc-url "$RPC" 2>/dev/null || echo 꺼짐)"
  printf 'API     live %s · ready %s\n' "$(curl -s -o /dev/null -m 3 -w '%{http_code}' "$API/health/live")" \
    "$(curl -s -o /dev/null -m 5 -w '%{http_code}' "$API/health/ready")"
  printf '웹      %s  http://127.0.0.1:%s/business.html?mode=api\n' \
    "$(curl -s -o /dev/null -m 3 -w '%{http_code}' "http://127.0.0.1:$WEB_PORT/business.html")" "$WEB_PORT"
  if alive api; then printf 'AI      %s\n' "$(cat "$RUN/api.mode" 2>/dev/null)"; else printf 'AI      -\n'; fi
}

down() {
  for p in web api anvil; do alive $p && kill "$(cat "$RUN/$p.pid")" 2>/dev/null; rm -f "$RUN/$p.pid"; done
  docker stop "$PG_NAME" >/dev/null 2>&1 || true
  say "껐어요. 데이터는 남아 있어요(다시 켜기: scripts/rc_local.sh up)"
}

case "${1:-}" in
  up)
    for t in docker uv anvil cast forge node curl openssl; do command -v $t >/dev/null || die "$t 이(가) 없어요"; done
    mkdir -p "$RUN/logs" "$RUN/secrets"; chmod 700 "$RUN/secrets"
    llm_env
    start_db; start_chain
    if [ -f "$RUN/wallet.env" ]; then
      api_env   # 이미 만든 환경도 새 migration(예: #139 accounts.email)을 받아야 API가 뜸
      "${UVR[@]}" alembic -c apps/api/alembic.ini upgrade head > "$RUN/logs/migrate.log" 2>&1 || die "migration 실패(logs/migrate.log)"
      start_api; ensure_accounts; write_bulk; write_samples
    else first_setup; fi
    echo; status
    echo; say "로그인 계정 v5_bank · 비밀번호: $RUN/secrets/test-accounts.json 의 password 값"
    say "개인 회원 rc-viewer@example.invalid · 비밀번호 같음"
    say "실제 AI 확인 계정 rc-ai-tester@example.invalid · 비밀번호 같음 · 10분 분석·업로드 제한 없음(#116 반영 시)"
    say "검증용 붙여넣기 문장: $RUN/verify-samples.txt" ;;
  status) status ;;
  down) down ;;
  db-tamper)
    got=$(db_amount 4300000); [ "$got" = 4300000 ] || die "대상 안내문을 못 찾았어요(시연 문자 원본이 발행됐는지: up)"
    say "서버 DB의 은행 #10 안내문 금액을 430,000원 → 4,300,000원으로 바꿨어요(체인 기록은 그대로). 되돌리기: scripts/rc_local.sh db-restore" ;;
  db-restore)
    got=$(db_amount 430000); [ "$got" = 430000 ] || die "대상 안내문을 못 찾았어요"
    say "서버 DB의 은행 #10 안내문 금액을 원래 430,000원으로 되돌렸어요" ;;
  purge)
    down; docker rm -f "$PG_NAME" >/dev/null 2>&1 || true; rm -rf "$RUN" "$MANIFEST" "$PRESET_FILE"
    say "재현 환경을 모두 지웠어요" ;;
  set-key)
    mkdir -p "$RUN/secrets"; chmod 700 "$RUN/secrets"
    printf 'OpenAI API 키를 붙여 넣고 Enter (화면에 보이지 않아요): '; IFS= read -rs key; echo
    case "$key" in sk-*) ;; *) die "sk- 로 시작하는 키가 아니에요";; esac
    (umask 077; printf '%s' "$key" > "$KEY_FILE")
    say "저장했어요(이 컴퓨터에만, 0600). 실제 AI로 켜기: RC_LLM=openai scripts/rc_local.sh up" ;;
  clear-key)
    rm -f "$KEY_FILE"; say "키 파일을 지웠어요. 다음 up부터 mock입니다" ;;
  *) echo "사용: scripts/rc_local.sh up | status | down | purge | set-key | clear-key | db-tamper | db-restore"; exit 2 ;;
esac
