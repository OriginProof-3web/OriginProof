# D G07 후속 반복 재현 절차 (미실행)

2026-10-21 확인: #86 `61703197399a2f66f18a3e0fcae51fd2bf54131f`는 미병합입니다. 현재 G07은 OPEN이며 이 문서는 준비 절차입니다. 과거 fresh18 PASS/mixed17 PASS1 FAIL, 이후 임시 반복 통과는 서로 다른 실행 근거로 보존합니다. C의 반복 통과와 B의 합성 검사 의견을 D 독립 재검증으로 대신하지 않습니다.

## 실행 전에 받을 인계

B/C가 #86 병합·외부 리뷰를 마친 **동일한 불변 제품 SHA**, Reader/Writer/indexer/ABI·배포 manifest·lockfile·실행 명령을 전달해야 합니다. 그 SHA에 #86이 포함되는지 `git merge-base --is-ancestor 61703197399a2f66f18a3e0fcae51fd2bf54131f <candidate SHA>`로 확인합니다. 이후 보완 커밋이 있으면 최신 수정 계보도 확인합니다. 공유/보존 phase에 직접 commit하지 않습니다.

## 사용할 기존 자산과 필요한 전환

- [w5_p0_api_qa.py](../../fixtures/finals/w5_p0_api_qa.py)의 fresh/mixed 모드와 [projection QA](../../fixtures/finals/w5_projection_qa.py)를 재사용합니다. 현재 runner의 PRODUCT_SHA는 과거9651062로 고정돼 있습니다. **이 runner를 그대로 실행하면 새 #86 제품 검증이 아닙니다.**
- D 검증 branch/격리 clone에서만 PRODUCT_SHA를 C가 준 후보로, DEPLOYER 태그도 해당 SHA로 맞춥니다. 후보 lockfile과 실행 환경을 일치시키고 기존 `materialize()` lockfile 동일성 검사를 유지합니다. 검증 소스/제품 SHA·변경 diff를 따로 기록합니다. 원본 helper SHA는 고정 재사용 원본으로 유지합니다.
- 예전 lockfile을 복사해 맞추거나 일치 검사를 삭제하지 않습니다. 새 의존성/공유 경로 변경이 필요하면 C와 조율합니다. 유료 key를 child 환경에서 제거하고 mock을 사용합니다.

## 실제 실행 순서와 판정

1. 새 소유 PostgreSQL/Anvil/API 프로세스에서 fresh를1회 실행하고 원본/manifest/checkpoint·receipt 근거를 보존합니다.
2. 동일한 후보 SHA에서 mixed를 최소3회, 각 회 새 격리 자원으로 반복합니다. RPC stop/start→projection replay→worker 재시작/reorg→ordered lifecycle의 순서와 추가 Anvil 재시작을 유지합니다. 실행 순서를 바꿔 실패를 감추지 않습니다.
3. 같은 chain ID의 새 빈 RPC/다른 배포 block hash 거부, 정상 같은 배포의 restart 후 복구, receipt 유실/UNKNOWN 동일 Operation 재조회, checkpoint 보존·canonical reorg 대조를 각각 확인합니다.
4. 각 회 명령은 `W5_D_API_QA=1 .uv-venv/bin/python fixtures/finals/w5_p0_api_qa.py`, mixed는 `W5_D_MIXED_STACK_QA=1`도 설정합니다. 앞 절의 후보/lockfile 전환과 검토 후에만 실행합니다.
5. 회차별 `build/w5-d-api/<UUID>/summary.json`·소스 SHA·fingerprint·실패 로그·resources_closed를 보존합니다. 기대 정상 verify가 INCONCLUSIVE/UNAVAILABLE이면 실패로 남기며 skip/xfail/retry 성공으로 대체하지 않습니다.
6. 같은 후보에서 Reader/Writer/indexer 단위·receipt/checkpoint 회귀와 C 실제 프로세스/DB복구 검사도 구분해 기록합니다. B/C 원인 수정 확인과 D 반복 결과가 모두 있을 때만 G07 종료를 제안합니다. 브라우저·신규 지갑 수용/단계 완료와는 별개입니다.

현재는 **0회 실행 / G07 미해결**입니다. 준비만으로 레거시 runner를 새 제품 검증 완료로 보고하지 않습니다.
