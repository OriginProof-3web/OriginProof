# W1-D2 합성 QA 입력

기준: 개발 계획서 v3.0 §15.2·§16, ADR 0001. 자료 버전 1.0.0,
대상 정책의 schema version 2.0.0. `cases.json`은 **서명되지 않은 QA 입력**이다.
C의 v2 모델·OpenAPI 또는 Golden Fixture를 대체하지 않는다.

두 합성 기관/유형의 `envelope_fields`에는 signature가 없다. binding과
payload hash는 기존 originproof_core.payload_hash를 재사용한다. 고정 token,
salt, nonce는 공개된 합성 테스트 재료이며 실제 발행의 무작위 생성 대체물이 아니다.
기관 코드·ID는 QA용 예시이며 C가 제공할 계정/기관 seed와 연결 시 대응시킨다.

생성 (저장소 루트):

```sh
PYTHONPATH=packages/python .uv-venv/bin/python fixtures/finals/build_cases.py
```

재현 절차:

1. profile의 합성 입력을 C의 실제 v2 발행 모델/생성기에 연결한다.
   실제 발행에서는 서버가 시각·ID·nonce·수신자 binding을 생성한다.
2. C 생성기로 서명하고 실제 배포에 등록한 fixture만 서명/체인 검사에 사용한다.
   기존 v1 Golden은 그대로 보존한다.
3. 각 case의 actor/action을 실제 테스트 계정/API에 대응시킨다.
   API route·오류 status는 C1/C3 생성 계약 확정 후 기록한다.
4. changes는 scenario 조건이다. observed_patch는 받은 자료의 한 필드만
   바꾸며 원본 Proof/envelope를 다시 서명하거나 수정하지 않는다.
   envelope_patch는 서명 대상 변조/환경 오류 검사다.
5. clock은 합성 서버 시계를 주입해 경계를 재현한다. OS 시간을 바꾸지 않는다.
6. expected는 ADR의 조건부 기대값이다. preconditions를 충족하지 못하면
   VERIFIED 기대값으로 실행하지 않는다. 권한 거부 시 제한 비교 결과도 노출하지 않는다.
7. 실제 실행 SHA·검사 계층·기대/실제 결과·상태 변화를 별도 보고한다.
   현재 모든 case는 NOT_RUN이며 자료 무결성 검사 성공으로 변경하지 않는다.

현재 검사는 합성 자료의 binding/hash·변조 분리·기간 경계·ID/출처를 검사한다.
로그인/신청 서버, v2 검증 코어, 브라우저 또는 실제 체인의 통과 증거가 아니다.
F01~F15 전체 수용 사례는 [D 사례표](../../docs/qa/w1-acceptance-matrix.md)를 참조한다.

## W3 독립 모델·코어 사례

`w3_cases.json`은 기존 W1 자료와 분리한 fixture 1.0.0입니다. C의 공개 서명 Golden을
읽어 지급 요청 31개·공식 문서 33개를 구성하며 Golden/기존 cases.json을 수정하지 않습니다.
domain/기간/타입 모델 거부와 정상·누락·변조·서명·신뢰 입력 경계를 검사합니다.

```sh
PYTHONPATH=packages/python .uv-venv/bin/python fixtures/finals/build_w3_cases.py
make test-analyzer
```

실행 결과는 [W3-D 보고](../../docs/qa/w3-d-acceptance.md)에 기록합니다. manifest의
`live_execution_status=NOT_RUN`은 실제 발행/DB/RPC/브라우저 미실행을 뜻합니다.
코어 검사 통과로 이를 PASS로 바꾸지 않습니다. W3 모든 결과의 lifecycle은 null,
Proof 상태 검사는 NOT_RUN이며 실제 현재 사용 가능 상태를 주장하지 않습니다.
