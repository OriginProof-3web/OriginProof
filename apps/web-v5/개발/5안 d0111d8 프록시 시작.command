#!/bin/zsh
# 5안 화면(페이지/)을 같은 출처로 내보내고 /api/* 를 d0111d8 API 로 넘기는 프록시(T2). 본부가 실행한다.
# 먼저 d0111d8 작업 폴더에서 make finals-up 으로 API(기본 http://127.0.0.1:8000)를 켠다.
# 바꾸고 싶으면: OP5_PROXY_PORT=8791 OP5_UPSTREAM=http://127.0.0.1:8000 ./'5안 d0111d8 프록시 시작.command'
cd "${0:A:h}" || exit 1
command -v node >/dev/null || { echo "node 가 없어요"; exit 1; }
export OP5_PROXY_PORT="${OP5_PROXY_PORT:-8790}"
export OP5_UPSTREAM="${OP5_UPSTREAM:-http://127.0.0.1:8000}"
echo "브라우저에서 열기: http://127.0.0.1:${OP5_PROXY_PORT}/business.html?mode=api"
exec node op5-proxy.mjs
