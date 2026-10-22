# D 병합 후 검증·G07 범위 판정 — 2026-10-22

계획서5.1 / v5-shared-0.2. 팀에서 D #72~#76과 B #78/#79, C #85를 병합한 뒤 phase/W5 `f6e7fdb6727f6b7957d8acc7f3e0bf7e7674ea5f`에서 별도 D `codex/v5-d-postmerge-qa`를 만들었습니다. 기존 branch/커밋·사용자 원본·보존 phase를 유지했습니다. 공유 phase에서 직접 개발하지 않았으며 이 작업이 PR 병합이나 승격을 실행한 것은 아닙니다. [구조화 결과](v5-d-postmerge-20261022.json).

## 병합·리뷰와 기존 개발 결과

#76 최종 head9270a84는 2026-10-22 09:21:42 KST에 be93c7f로 병합됐습니다. [대표의 같은 HEAD 승인](https://github.com/OriginProof-3web/OriginProof/pull/76#pullrequestreview-5607814995)을 확인했습니다. 제한 평가 실행기·0600 journal/중단재개·수용 증거 도구·실제 독립 로컬 검증과 첫 하네스 실패/수정 이력은 [원래 개발 보고](v5-d-development-completion-20261021.md)에 보존합니다. 실제 EVM/CLI 실행5b50ac4 및 G07의 기존 두 제품 SHA를 이번 phase 실행 SHA로 바꾸지 않습니다.

[최종 D CI](https://github.com/OriginProof-3web/OriginProof/actions/runs/39591674050)의 artifact를 내려받아 stage43/consumer31/성능16/독립71(C49+D22), failure/error/skip0을 확인했습니다. [최종 Quality Gate](https://github.com/OriginProof-3web/OriginProof/actions/runs/39591674030)는 Python788 PASS/기존 opt-in10 SKIP, 보안 감사0건, 실제 폐기 DB/API 복구2 PASS, Foundry/웹/생성물 검사 통과입니다. 원래 #76의6종 CI와 병합 뒤 Discord 통지는 다른 항목입니다.

## 병합 후 같은 phase 검사

| 검사 | 실제 결과·범위 |
| --- | --- |
| 기본 전체 Python | **953 PASS / opt-in11 SKIP / 기존 Starlette 경고1** |
| supporting 수용 도구 | stage43/consumer31/성능16/D독립22 PASS, skip0, source_consistent=true |
| 별도 D guard/G07·수용 도구·고정 C63 | **124 PASS** =16+27+10+D22+C49 |
| make generate·Ruff·diff | PASS / 생성물 차이 없음 |

기본11 SKIP은 기존 opt-in10개에 이번 phase에 병합된 B의 `test_wallet_live.py` 일회용 EVM 검사가 추가된 것입니다. 통합 범위가 늘어난 결과이며 D 필수 검사 누락/skip 허용으로 바꾸지 않았습니다. supporting 도구는 실제 수용 BLOCKED/exit2를 유지하며 W1~W7 완료를 선언하지 않습니다. 겹치는 수를 합산하지 않습니다.

별도 도구 첫 명령에서 macOS 기본 Git shim이 선택돼 G07 단위27개가 setup error였고 나머지97개는 통과했습니다. 설치된 Command Line Tools PATH로 해당27개만 다시 실행해 통과했습니다. Xcode 라이선스/시스템 설정이나 코드를 바꿔 우회하지 않았습니다. 실제 G07 fresh/mixed 실패가 아닙니다.

## G07: 로컬 legacy 범위 해결

**판정: RESOLVED_LOCAL_LEGACY.** 기준 문서 반영이나 한 번의 비재현만으로 닫은 것이 아닙니다.

1. 원인은 Anvil1.4.4 상태 재기동 때 genesis만 다시 생성되는 문제로 확인됐고, #86이 기존 Reader/Writer의 배포 블록 기준 식별을 보존하도록 수정했습니다.
2. 실제 D 실행은 제품d757a26의 fresh1/mixed3와 제품33396ba의 fresh1/mixed5이며 전 회18개 필수 그룹 통과·자원 정리 true입니다. 다른 체인·같은 ID의 빈 RPC·배포 식별 거부, projection/reorg/재시작, receipt/Operation/checkpoint 회귀를 포함합니다. 이전17 PASS/1 FAIL과 원인 진단 기록은 그대로 둡니다.
3. [B 검토](https://github.com/OriginProof-3web/OriginProof/pull/76#issuecomment-6314138173)와 [C 최종 검토·해결 판정 동의](https://github.com/OriginProof-3web/OriginProof/pull/76#issuecomment-6318989928)를 확인했습니다. C는 두 D 실행과 거부 경계·수정 전 실패를 대조했고 G07에 한정해 판정 동의를 밝혔습니다. 평가 실행기 등 다른 변경의 C 승인으로 확대하지 않습니다.

이 후속 작업에서 live G07을 다시 실행한 것으로 기록하지 않습니다. 새 지갑/Registry/API의 실제 통합·공개 체인·브라우저·단계 완료는 이 해결 범위 밖입니다. 해당 경계에서 새 결함이 나오면 별도 후보·재현 근거로 추적합니다.

## 남은 인계와 사람 확인

- #84에는 [A의 소비 검토](https://github.com/OriginProof-3web/OriginProof/issues/84#issuecomment-6334429744)와 [대표 지시의 B/D 대행 검토](https://github.com/OriginProof-3web/OriginProof/issues/84#issuecomment-6334500736)가 있습니다. D 본인 확인과 Codex의 기술 실행은 구분합니다. 사용자 본인의 대행 변경 확인 코멘트는 AI가 대신 게시하지 않았습니다.
- B 읽기 Adapter는 병합됐지만 submit/find_transaction은 명시적인 dependency 오류이며 C 생산 주입·중계/Operation 연결, A 실제 왕복은 후속입니다. 실제 API 성능·새 지갑 브라우저/DB/보관·복구 수용과 구분합니다.
- 입력 종류/우선순위·라벨/분할 사람 리뷰·유료 평가 범위/예산이 정해지기 전 실제 모델/보류36개 예측·미선정 변환을 실행하지 않습니다. 모델gpt-6-luna와 Decisions API 범위 밖 결정은 유지합니다.
- 선정 공개 환경(#89는 준비 PR), 다른 노트북·동일 RC3회, phase 승격의 별도 검사/리뷰가 남습니다. 과거 PR을 다시 병합하거나 이번 문서로 기능/단계 완료를 만들지 않았습니다.
