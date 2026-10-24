# W5 D 동일 HEAD 검사 보완

AI(Codex)가 앞 D PR의 JUnit 정확 수·summary·skip 보호와 indexer/uv.lock trigger를 merge로 이어받았습니다. 옛 별도 C 소스 조합은 [동일 HEAD 재현 안내](v5-d-review-fixes.md)로 대체했습니다.

로컬 guard 16 PASS / stage 31 PASS / consumer 31 PASS(각 0 FAIL / 0 ERROR / 0 SKIP)입니다. #75에는 W2/W3/W4 명시 QA가 있고 분석 연결 QA 파일 자체는 후속 #76에 있으므로 #75에 복제하지 않았습니다. JUnit `/private/tmp/originproof-d-w5-stage.xml`, `consumer.xml`을 검사했습니다. 분석기 경로 321개+consumer 31개도 별도 실행해 **352 PASS / 0 SKIP**, Starlette 경고 1개입니다(`/private/tmp/originproof-d-w5-analyzer.xml`). 각 실행 범위는 서로 겹치므로 합산하지 않습니다.

실행 소스는 이번 D 커밋 직전 working tree입니다. [W2 환경 기록](v5-d-same-head-w2-20261021.md)과 같은 기존 설치 환경이며 이 PR의 의존성/lockfile을 바꾸지 않았습니다. 잠금 환경 설치·보안 감사·GitHub 최종 SHA 결과는 별도로 확인합니다.

ASGI·SQLite·합성 Registry·mock/SDK transport 검사입니다. 유료 호출 0회, 모델 `gpt-6-luna` 선택 유지, 입력 종류/우선순위·A/C 라벨/분할 리뷰·유료 실행 범위/예산·원시 후보 인용 정확도/누락률/위치 정확도 평가는 미완료입니다. 실제 EVM/브라우저·G07·단계 완료·사람의 대행 확인/외부 승인은 선언하지 않습니다.
