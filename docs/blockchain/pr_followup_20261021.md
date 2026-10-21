# B PR 후속 검증 · 2026-10-21

사용자 요청으로 Codex가 B PR 보완·검사를 수행합니다. C 대행 변경의 기술 검증이며 여하민님의 직접 열람/승인 또는 작성자 외 리뷰를 대신하지 않습니다. PR의 현재 head 재리뷰·선행 조건이 충족되기 전에는 병합하지 않습니다.

## #64 · 기준 fb2d5a5

- C 대행의 phase/W5 병합·양쪽 export/기록 보존과 eth-abi API 실행 의존성 이동을 확인했습니다. 타 담당 기능을 재작성하지 않았습니다.
- 현행 manifest는 Python deploy_local.py가 생성하는 deployment ID·block/hash·genesis·ABI hash·roles 형식이며 `31337.local.json`입니다. 옛 1.0.0 예시/샘플은 bytes를 보존해 deployments/legacy/로 옮겼습니다. legacy shell은 `<chain>.legacy.local.json`에만 쓰며 현행 파일을 덮어쓰지 않습니다. 가짜 commit/hash로 현행 manifest를 만들지 않았습니다.
- eth-abi5.2.0(실행), parsimonious0.10.0·regex2026.9.29(전이), respx0.23.1(개발 검사)은 기존 B/통합 lock의 의존성입니다. 10/21 사용자는 이 PR들의 보완·검증·공유 진행을 지시했습니다. 이번에 새 패키지나 버전을 추가하지 않았습니다. 별도 C lockfile 조율 승인/작성자 외 확인은 요청하며 받았다고 가정하지 않습니다. #83의 FastAPI 등 승인과 이 항목을 혼동하지 않습니다.
- `uv sync --locked --no-dev --package originproof-api` 별도 신규 환경: pytest 미설치·eth-abi import·실제 Uvicorn startup/lifespan 및 HTTP `/health/live`200 확인. Docker와 같은 `PYTHONPATH=apps/api/src:packages/python:services/indexer/src`를 사용했습니다. DB readiness/API 업무·wallet 활성 연결을 확인한 것은 아닙니다.
- 검사 구성 중 indexer 경로 누락·옛 health 경로404·빈 wallet 주소 환경변수로 인한 실패가 있었고, 이미지 설정/실제 경로/기본 비활성 설정에 맞춰 재검증했습니다. 제품 오류를 숨기거나 성공 응답으로 바꾸지 않았습니다.
- Python609 PASS/10 SKIP, 기존 Starlette 경고1; 공식 ruff PASS. Foundry80 PASS(기존 phase 포함), shell 문법·lock 검사 PASS. CI는 새 head에서 별도 확인합니다.
- 원본 작업 폴더의 사용자 미커밋5개는 건드리지 않고 별도 managed worktree에서 진행했습니다.

## #68 · 대행 수정 2d1df07 / 기준 0459f4f

Registry가 이전 최신이 ACTIVE일 때만 SUPERSEDED 전이/이벤트를 수행하는 것을 읽고 확인했습니다. REVOKED의 저장 전체는 후속 발행 뒤에도 불변이며 새 nonce로 재철회해도 거부·nonce 불변을 검사합니다. 이미 SUPERSEDED인 과거 버전의 정당한 첫 철회는 유지합니다. Foundry 전체101개 PASS, Python609 PASS/10 SKIP, 기존 경고1입니다. B의 기술적 검증 결과이며 사람의 직접 승인·독립 재리뷰 완료가 아닙니다.

기존 Adapter의 `version>1`이면 무조건 Superseded 이벤트를 요구하는 부분은 이 규칙과 맞지 않아 #78에서 보완합니다. Contract·공통 정책을 다시 바꾸지 않습니다.
## 추가 확인 — #64 현행 manifest 경로

AI(Codex)가 여하민님 요청으로 수행했습니다. Reader·Writer의 합성 manifest fixture를 실제 현행 출력명 `31337.local.json`으로 맞춰 loader 경로 호환을 기존 정상/거부 검사로 확인합니다. 실제 배포 파일이나 원본 사용자 변경은 읽어 덮어쓰지 않습니다. 이 검사는 MockTransport이며 별도 no-dev Uvicorn 기동과 구분합니다.

현행 파일명 fixture 검사: Reader·Writer **104 PASS**. 새 패키지·버전 변경 없음.
