# D G07 후속 반복 재현 절차 (실환경 미실행)

#86 `61703197399a2f66f18a3e0fcae51fd2bf54131f`는 미병합입니다. 현재 G07은 OPEN입니다. 과거 fresh18 PASS/mixed17 PASS1 FAIL과 C/B의 후속 검사를 D의 동일 후보 독립 재검증으로 대신하지 않습니다.

## 실행 전 인계와 준비

B/C가 #86 외부 리뷰·병합 후 **불변 제품 SHA**, Reader/Writer/indexer·ABI·배포 manifest·lockfile·실행 명령을 전달합니다. #87 보안 수정도 현재 D QA와 동일한 잠금 환경에 반영돼야 합니다. 전용 clean D checkout에서 fetch하고 실제 후보를 반영해 소스/lockfile을 일치시킵니다. lockfile만 복사하거나 일치 검사를 삭제하지 않습니다. 공유·보존 phase에서 직접 작업하지 않습니다.

## 사전 검사 (서비스를 띄우지 않음)

```sh
git fetch --prune origin
# CANDIDATE_SHA는 B/C가 전달한 40자리 고정 commit SHA로 설정
.uv-venv/bin/python fixtures/finals/v5_d_g07_runner.py --product-sha "$CANDIDATE_SHA"
```

runner는 현재 phase가 #86을 포함하는지, 후보가 현재 phase를 포함하는지, QA가 clean인지, 후보 uv.lock과 QA uv.lock이 같은지 검사합니다. READY_TO_EXECUTE_NOT_TESTED는 준비 조건만 충족했다는 뜻입니다. BLOCKED/exit2이면 실제 환경은 기동하지 않습니다. 미래 #86 수정이 squash/rebase돼 원본 SHA 계보가 바뀌면 C의 실제 병합 근거를 확인하고 guard 기준을 리뷰로 갱신해야 합니다.

## 준비 조건 충족 후 명시 실행

```sh
.uv-venv/bin/python fixtures/finals/v5_d_g07_runner.py \
  --product-sha "$CANDIDATE_SHA" --execute --mixed-runs 3
```

- 후보와 같은 lock의 `uv run --locked` 환경에서 기존 w5_p0_api_qa.py를 실행합니다. 과거 runner의 PRODUCT_SHA를 수동 편집하지 않습니다. 기본 과거 실행과 명시 후보 실행은 metadata에서 구분합니다.
- fresh1회 뒤 mixed3회(최대20회 지정 가능), 각 회 독립 DB/Anvil/프로세스와 출력 디렉터리를 사용합니다. fresh 실패 시 중단합니다. mixed의 실패는 후속 성공으로 덮지 않습니다.
- RPC stop/start→projection replay→worker 재시작/reorg→ordered lifecycle·추가 Anvil 재시작 순서를 유지합니다. 다른 chain ID/같은 ID 빈 RPC/배포 block hash 불일치 거부, receipt 유실·UNKNOWN 동일 Operation, checkpoint 보존·canonical reorg를 포함한18개 필수 그룹이 모두 있어야 합니다.
- 보고서는 `build/w5-d-g07/<UUID>/summary.json`, 회차별 legacy 보고서·private runner.log를 연결합니다. 제품/QA SHA·lock hash·mode·예상 그룹·mock/paid0·resources_closed를 확인하며 missing/skip/중복/잘못된 SHA는 실패입니다.
- 통과 상태도 PASS_REQUIRES_B_C_REVIEW입니다. B/C의 원인 수정·리뷰와 D의 실제 반복 근거를 확인한 뒤 G07 종료를 제안합니다. 신규 지갑/브라우저 수용·단계 완료와 구분합니다.

## 현재 실행 상태

도구27개 단위 검사는 임시 Git 이력과 simulated child로 PASS입니다. 현재 phase를 넣은 실제 CLI 사전 검사는 #86 미반영·lock 불일치로 BLOCKED였습니다(개발 중 dirty도 차단). **실제 fresh/mixed 실행0회 / G07 미해결**입니다. Docker·운영/데모 DB·실제 모델은 실행하지 않았습니다.

[구현·지표·전체 검사 근거](v5-d-development-tools-20261021.md).
