# B PR 마무리·사람 리뷰 준비 — 2026-10-21

AI(Codex)가 여하민님 요청으로 기술 검증과 이 초안을 작성했습니다. **아래 사람 문안은 게시하지 않았고, 담당자 직접 확인·Approve·병합도 하지 않았습니다.** 확인된 원격 리뷰의 최신 시각은 2026-10-20 00:56 UTC(4차), 이후 코멘트까지 다시 읽었습니다. 지시서의 “#69·#78·#79 없음” 표와 달리 48a8419/07f95d9/d38f597에 후속 수정이 이미 있어 재적용하지 않았습니다.

## 수행·검사

| 대상 | 실제 결과 |
| --- | --- |
| #64 | legacy manifest/명령 분리·no-dev Uvicorn /health/live 200 기존 증거 유지. 현행 31337.local.json fixture로 Reader/Writer 104 PASS. Python609 PASS/10 SKIP 및 Foundry80은 40ade0e 시점 실행 이력이며 이후 fixture/문서만 변경 |
| #68 | ACTIVE만 SUPERSEDED, REVOKED 불변·재철회 nonce 불변. Foundry101 PASS(동일 Contract 소스 최종 후보 재실행 포함). base 변경·병합 없음 |
| #69 | 정확한 custom error 앞당김·BigInteger·입력/ABI 경계 보강 유지. 98e3709에 [기존 PostgreSQL 마이그레이션](../../services/indexer/migrations/README.md)·2^31 초과 위치 보존 검사 추가(해당 파일58 PASS). [C port 설계 메모](w5_port_integration_design.md)는 합의용 초안이며 연결 구현 아님 |
| #78 | 4b010a5의 revoke state==2 유지, revoked predecessor 뒤 publish의 Superseded 비필수와 ACTIVE일 때 필수 보존. 관련 RPC/Reconciler112 PASS |
| #79 | 최종 실행 SHA `4d7023ec0c903ca98a8beaf7cbd9b0c04cd3b707`에서 API/indexer/core507 PASS/9 SKIP, Foundry101 PASS, 별도 실제 Anvil1 PASS. [새 실행 증거](evidence/v5_w5_live_4d7023e.json). fresh-client 직렬화 intent 복구·tx hash 없는 검색·반복 조회 nonce 불변·revoked v2 뒤 v3 발행 확인 |

최종 후보 make lint·make typecheck PASS(Python Ruff/compileall·웹 ESLint/TypeScript). 실행 중 pnpm이 기존 lock의409개를 로컬 캐시에서 자동 복원했습니다. 다운로드0·버전/lockfile 변경0이었으나 “새 설치 금지”를 고려해 이 자동 동작을 미리 차단하지 못했습니다. 추가 설치는 하지 않았습니다. 임시 worktree의 생성 의존성 링크·캐시 복원 파일만 정리하며 원본 사용자 작업은 보존합니다.

PostgreSQL 실제 migration은 psql 미설치·Docker daemon 부재로 미실행입니다. SQL은 기존 행·PK·checkpoint를 보존하는 명시적 운영 적용본이며 create_all을 migration으로 취급하지 않습니다. C Operation/API DB 프로세스 재시작·production submit·공개 네트워크·D mixed QA는 미실행. 기존745 PASS/11 SKIP는 b92be2e의 전체 Python(분석기 포함) 실행으로, 이번 요청 범위507 PASS와 합산하지 않습니다.

## #86 기술 검토 초안 — 사람 게시 전 확인

검토 head `61703197399a2f66f18a3e0fcae51fd2bf54131f`. Reader/Writer의 매 작업 genesis 조회만 제거하고 chain ID·배포 block/hash·code 검사는 유지합니다. manifest의 genesis·deployment_id는 기록/격리 식별자로 유지하므로 이전 receipt/checkpoint를 새 배포로 바꾸지 않습니다. 배포 블록의 ancestry commitment를 신뢰하는 기존 RPC 경계 안에서 Anvil --state의 genesis 응답 재생성에 대응하는 방향은 타당합니다. 배포 block=0 설정이면 여전히 배포 블록으로0번을 검증합니다.

고정 SHA의 임시 소스에서 기존 설치 환경으로 Reader/Writer/checkpoint **115 PASS**(genesis_regenerated와 deployment mismatch·receipt/recovery·projection reorg 포함). 최초에는 해당 PR에 없는 test_legacy_projection.py 경로를 넣어 수집 실패했으며 실제 존재하는 세 파일로 정정했습니다. C branch를 checkout/merge/수정하지 않았습니다.

사람 의견 초안: “배포 블록 식별 유지·genesis 재조회 제거 방향과 합성 회귀 결과를 검토했습니다. 이 검토는 실제 Anvil mixed QA 재현이나 G07 종료 판정이 아닙니다. 병합 뒤 D가 배포 식별 불일치 거부·receipt/checkpoint 회귀를 포함한 mixed QA를 반복한 뒤 G07 판정을 갱신해 주세요.”

## #83 기술 검토 초안 — 사람 게시 전 확인

검토 head `7ac868e8683633d831f2ecd32f584b2a0feae7e1`. PR 자체는 문서만 바꾸며 원래 상향은 phase의 선행 커밋입니다. 승인 기록에 fastapi0.142.2·starlette1.7.0·pytest9.1.1·pytest-asyncio1.4.0 및 annotated-doc/opentelemetry-api 전이 항목이 있는 것을 확인했습니다. C의 조율 승인 기록을 작성자 외 리뷰로 세지 않습니다. eth-abi/respx는 별도 B #64 기록입니다.

설치/버전 변경 없이 위 네 버전의 기존 venv와 #83 고정 SHA의 임시 소스로 blockchain/indexer **123 PASS/2 live SKIP**. B 최종 후보에서도 API/indexer/core507 PASS/9 SKIP. Starlette TestClient의 기존 deprecation 경고 이력은 기록하되 검사 통과를 운영 전체 호환성 보장으로 해석하지 않습니다.

사람 의견 초안: “B blockchain/indexer의 지정 의존성 조합 합성 회귀123 PASS/2 SKIP를 확인했습니다. 문서의 전이 의존성·이전 변경 출처 표기를 확인했습니다. D analyzer 영향 확인과 작성자 외 리뷰는 별도 필요합니다. certifi·pillow 보안 감사 공통 실패는 C 보안 PR로 처리하고 이 검토를 근거로 무시하지 않습니다.”

## PR별 담당자 직접 확인 문안 초안

**여하민님이 아래 파일·커밋과 검사 결과를 직접 읽고 동의한 뒤, 맞는 내용으로 수정해 직접 게시하는 문안입니다. AI가 사람의 직접 확인 사실을 증명하지 않습니다.**

- #64: “대행 반영 fb2d5a5와 후속 manifest·실행 의존성 분리 변경을 확인했습니다. 현행 배포와 legacy 예시를 구분하며 B 설계와 맞습니다. 의존성 채택 기록과 clean runtime 근거를 확인했습니다.”
- #68: “대행 0459f4f 및 수정2d1df07을 확인했습니다. ACTIVE만 SUPERSEDED로 전이하고 REVOKED 전체 저장/재철회 nonce를 보존하는 방향에 동의합니다.”
- #69: “대행 c5a82cc와 후속 custom error·BigInteger·마이그레이션 설계를 확인했습니다. C port 연결은 설계 초안이며 완료가 아님을 확인했습니다.”
- #78: “대행4918ef1/4b010a5와 후속 Adapter 수정을 확인했습니다. revoke는 state==2이며 이전이 REVOKED인 발행은 대체 이벤트를 요구하지 않고 ACTIVE 이전은 계속 검증하는 방향에 동의합니다.”
- #79: “대행42ea605와 후속 로컬 Anvil 결과를 확인했습니다. fresh-client 원본 검색·재조회 nonce 불변을 확인했으나 C API/DB Operation 재시작과 공개 네트워크는 미검증임을 이해했습니다.”

## 사람이 GitHub에서 할 일

1. 위 확인 초안을 직접 검토·수정 후 각 PR에 게시. #86·#83 리뷰도 직접 결정. AI 기술 검증과 사람 리뷰를 구분.
2. #69/#78/#79 Draft 해제는 최신 리뷰가 요구한 C 연결·실제 API/DB·독립 리뷰 조건과 맞는지 먼저 확인. 설계 메모 대안을 허용한 이번 지시서와 #78 기존 연결 요구를 리뷰어와 조율하고 완료로 오기하지 않음.
3. #64 병합 뒤 #68 base를 phase/W5로 사람이 변경. 이후 순서는 #83→#64→#86→#68→#69→#78→#79를 따름. 이번 작업에서 PR 병합은 하지 않음.
4. 각 PR 현재 head의 CI와 공통 보안 수정 반영 후 재리뷰 요청. 직전 작업에서 이미 kimhyounjun에게 재요청했지만 이 지시서 이후에는 사람 코멘트/Approve를 대신 게시하지 않음.

계획5.1·공통 준비0.1 유지, C 후속0.2는 별도 소비 초안. 입력은 회의 후 확정·Decisions API 범위 밖·v1/v2 회귀와 G07 미해결 유지. 기한은 문서의2026-10-24 18:00을 그대로 기록하되 요일 표기는 달력과 대조가 필요합니다(10/24는 토요일). 팀 단톡 메시지는 발송하지 않았습니다.
