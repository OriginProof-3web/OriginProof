#!/bin/zsh
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd -- "$(dirname -- "$0")" || exit 1

# Build the source beside this launcher so W5/W6/W7 edits appear in the same page.
if ! command -v node >/dev/null; then
  print '화면 빌드에 Node.js가 필요합니다.'
  exit 1
fi
if ! node -e "for (const name of ['esbuild', 'qrcode', 'react', 'react-dom', 'lucide-react']) require.resolve(name); require('node:fs').accessSync('node_modules/.bin/tailwindcss', 1)" >/dev/null 2>&1; then
  print '화면에 필요한 기존 패키지를 설치합니다.'
  if ! npm ci --ignore-scripts; then
    print '패키지 설치에 실패했습니다.'
    exit 1
  fi
fi
if ! node build.mjs; then
  print '최신 화면 빌드에 실패했습니다. 위 오류를 확인해 주세요.'
  read 'reply?Enter를 누르면 닫힙니다. '
  exit 1
fi

url='http://127.0.0.1:8768/index.html'
health_url='http://127.0.0.1:8768/admin.html'
server_pid=''
ready() {
  curl --fail --silent --max-time 1 -H 'Content-Type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' 'http://127.0.0.1:18546' | grep -Eq '"result"[[:space:]]*:[[:space:]]*"0x7a69"' || return 1
  curl --fail --silent --max-time 1 'http://127.0.0.1:8768/api/health/ready' >/dev/null || return 1
  curl --fail --silent --max-time 1 "$health_url" | grep -q '<title>OriginProof — 관리자</title>'
}
cleanup() {
  if [[ -n "$server_pid" ]]; then
    kill "$server_pid" 2>/dev/null
    wait "$server_pid" 2>/dev/null
  fi
}
trap cleanup EXIT
trap 'exit 0' INT TERM

if ready; then
  open "$url"
  print '실행 중인 서버의 메인 페이지를 열었습니다.'
  exit 0
fi
if ! command -v python3 >/dev/null; then
  print 'Python 3가 필요합니다. Python 설치 후 다시 실행해 주세요.'
  read 'reply?Enter를 누르면 닫힙니다. '
  exit 1
fi

python3 local-runtime.py &
server_pid=$!
for attempt in {1..1500}; do
  if ready; then
    open "$url"
    print '협업 테스트 서버가 켜졌습니다.'
    print '메인 페이지에서 개인 로그인 후 관리자 페이지로 들어가세요.'
    print '서버를 종료하려면 이 창에서 Control+C를 누르세요.'
    wait "$server_pid"
    exit $?
  fi
  if ! kill -0 "$server_pid" 2>/dev/null; then
    break
  fi
  sleep 0.2
done
print '서버를 시작하지 못했습니다. 위 오류를 확인해 주세요.'
read 'reply?Enter를 누르면 닫힙니다. '
exit 1
