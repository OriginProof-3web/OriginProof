# W2 A 수용 검사 보완 — 2026-10-06

- 담당: 김형준 / A / @kimhyounjun. Codex가 구현·검사·기록을 수행했습니다. Git 작성자 설정은 `khj <khj@local>`이며 팀원 확인을 대신하지 않습니다.
- 범위: W2-A1/A2, D PR #51의 여섯 UI 수용 실패 보완. 시작 `phase/W2` = `6f508fe6ae5ce106999c171e8205978dd2201333`.
- 검증 코드: `84fb5f2c03868b050290ba3d1da0b234eb22fc7f`. 문서 추가 커밋은 실행 SHA와 별도입니다.
- 기존 API·생성 타입·CSRF·Operation·권한 모델을 재사용했습니다. API/Contract/D 원본 파일과 lockfile을 변경하지 않았습니다.

## 변경

| 이전 문제 | 변경 및 확인 |
| --- | --- |
| ACTIVE 상태 설명 누락 | 실제 상태를 ‘활성화 완료’로 표시 |
| 승인 안내의 잘못된 dl 자식 | dt/dd 구조, axe definition-list 검사 |
| 키 목록 미조회 | 실제 GET, 공개 signer/기간/배포/키 ID만 표시 |
| 등록 화면 placeholder | 사유·UTC 기간·CSRF·request_id로 실제 POST |
| 폐기 UI 누락 | 사유·명시 확인·실제 POST·새로고침 상태 유지 |
| DB 승인 후 체인 활성화 UI 누락 | 운영자 활성화 POST, 실제 Operation 및 재조회 |

UNKNOWN은 성공으로 표시하지 않습니다. 키 작업 복구는 기존 Operation ID를 조회/복구하며 새 변경을 자동 재전송하지 않습니다. 401은 세션과 키 화면을 비우고 429는 대기 안내만 제공합니다.

## 재현

새 clone에서 아래 명령을 실행합니다. Docker와 저장소의 기존 pnpm/uv, Playwright Chromium이 필요합니다. localhost의 새 합성 PostgreSQL(tmpfs)·Anvil·API·Next production 서버만 사용하며 기존 관리자 서버/DB를 초기화하지 않습니다.

```sh
git fetch origin phase/W2 test/w2-d-browser-qa
pnpm install --frozen-lockfile
uv sync --all-packages --all-groups --locked
pnpm --filter originproof-demo-web lint
pnpm --filter originproof-demo-web typecheck
pnpm --filter originproof-demo-web test
W2_BROWSER_QA=1 uv run python apps/web/test/run-w2-live.py
```

준비 도구는 D #51의 `17f78e300b04aa9395fb20f6f76f5313d705db3d`에서 읽습니다. 원본을 수정하지 않고 ignored build에 사본을 만듭니다. A가 수정한 검사에서는 실제 등록·폐기·기관 활성화 작업 3건의 CONFIRMED와 DB 최종 상태를 확인합니다. D 원래 검사의 ‘브라우저 쓰기 없음’ 기대와 다르므로 D 독립 재검증을 대신하지 않습니다.

계정·서명기는 ignored private build에만 보관합니다. 공개 증거에는 합성 검사 이름과 상태·배포 식별값만 넣었습니다. 기존 결과 경로가 있으면 재실행을 거부하므로 새 clone을 사용합니다. 기본 E2E의 live 검사 skip은 통과가 아닙니다.

## 실패와 해결

- 이전 placeholder 컴포넌트 mock이 새 키 GET 응답과 맞지 않아 실패했습니다. 실제 계약 기반 테스트로 변경했습니다.
- API 모듈 경로가 준비 runner 및 자식 Alembic 프로세스에 빠졌습니다. 기존 workspace 경로를 두 곳에 전달했습니다.
- 브라우저 12개 통과 후 이전 DB 기대가 실패했습니다. 추가된 실제 쓰기 3건을 검증하도록 A 사본을 보완하고 새 합성 환경에서 다시 통과했습니다.
- 작업 폴더의 ignored `.next/types/routes.d 2.ts` 중복 생성물 때문에 typecheck가 실패했습니다. 추적 소스 변경 없이 깨끗한 clone에서 typecheck를 통과했습니다.
- local-origin clone에 origin/phase/W2 ref가 없어 준비가 실패했습니다. 실제 GitHub phase/D refs fetch 후 새 환경으로 재실행했습니다.

## 기본 브라우저 회귀

`6385931`에서 기본 E2E는 mock HTTP 5개 통과, 실제 준비 환경이 없는 live 12개 미실행입니다. 실제 연결 12개 통과는 위 `84fb5f2` production 실행의 별도 결과입니다. 기존 3000 서버 재사용으로 다른 메인 화면에 접속한 실패를 제외하기 위해 임시 ignored config에서 clone의 dev 서버를 53117로 띄웠습니다. 원본 설정의 다른 항목은 그대로 사용했습니다. 이전 placeholder 버튼 기대와 Next route announcer를 포함한 strict alert selector를 실제 UI에 맞게 보완했습니다.

## 결과와 제한

실행 결과는 [보관된 요약](qa/2026-10-06/w2-a-results.json)을 따릅니다. mock AI만 사용했고 유료 호출은 없습니다. 실제 Chromium/HTTP/PostgreSQL/Anvil 검사이며 route mock은 없습니다. 같은 Mac의 clean clone 재현으로 다른 PC 재현을 주장하지 않습니다.

W2 수정의 작성자 외 코드 리뷰, D #51 독립 갱신, 최신 phase 병합 후 회귀, 전체 팀 W2 완료 판정은 남아 있습니다. W3 QR #48과 W4 #53 리뷰, W5 전체 접근성/오류, W6 장애·타 환경 재현, W7 RC/발표는 이번 PR의 완료 범위가 아닙니다.
