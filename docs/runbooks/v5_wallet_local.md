# v5 지갑 API 로컬 실행

C의 `/v3` 지갑 API를 로컬에서 띄우고 합성 계정·설정을 준비하는 절차입니다. 상세 API 계약과 한계는 [C API 인계](../api/v5_c_runtime.md)를 따릅니다.

## 지금 되는 것과 아직 안 되는 것

- 된다: `/v3` 경로·DB(migration 0007~0009)·기관 확인(명부·데모 메일·내부 승인)·서명 요청 저장·복구·분석 보관, 합성 Registry를 주입한 검사.
- 아직 안 된다: 실제 Registry 연결. 앱은 `create_app(wallet_chain=None)`으로 시작하므로 체인을 조회하는 `/v3` 기능은 `503 WALLET_REGISTRY_UNAVAILABLE`을 반환합니다. B의 Adapter가 `phase`에 들어온 뒤 4절대로 연결합니다.

## 1. 기동과 DB

```sh
make finals-up      # mvp-up → deploy-local → api-reload → finals-seed(P0 계정), 끝에서 /health/ready 200 확인
```

v5 계정만 확인할 때는 `make mvp-up`, `make db-upgrade`만으로도 2·3절을 진행할 수 있습니다. 다만 이때 `/health/ready`는 503입니다(6절).

## 2. v5 합성 계정

```sh
make v5-wallet-seed
```

명부 기관(`iss_origin_mock_bank`, `iss_origin_mock_office`)마다 신청자·내부 승인자 계정과 운영 승인자 3명을 만듭니다. 다시 실행해도 기존 계정을 유지하며, 같은 이름의 계정이 다른 역할/기관이면 멈춥니다. 비밀번호는 `API_SIGNER_DIRECTORY`의 `test-accounts.json`(0600)에 있고 출력하지 않습니다. 실행이 끝나면 아래 설정 두 줄을 출력합니다.

`.env.example`의 `API_FINALS_*_ISSUER_ID`(`iss_finals_*`)는 기존 v1/v2 데모 기관이며 v5 명부와 다릅니다. v5 기관 확인은 위 명부 ID 계정으로 진행합니다.

## 3. 설정 (`.env`)

| 변수 | 값 |
| --- | --- |
| `API_WALLET_REGISTRY_ADDRESS` | 새 Registry 배포 주소. Golden 예시 주소를 쓰지 않습니다. |
| `API_WALLET_INTERNAL_APPROVERS` | 2절 출력값(기관 ID → 내부 승인자 계정 ID) |
| `API_WALLET_OPERATOR_ADDRESSES` | 2절 출력값의 `<approverN wallet address>`를 Governance 배포 때 고정한 승인 지갑 3개 주소로 바꿉니다. |
| `API_WALLET_DEMO_EMAIL_ENABLED` | 데모 메일을 쓸 때 `true` |
| `API_WALLET_EMAIL_SECRET` | 32바이트 이상 비밀값. 예: `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`. Git·로그에 남기지 않습니다. |
| `API_WALLET_TEXT_INPUT_ENABLED` | 입력 결정(V5-Q01) 전 기본 `false`. 합성 검사에서만 `true` |
| `API_WALLET_RELAY_ENABLED` | 기본 `false`(기관 지갑 직접 제출). 서버는 기관 개인키를 보관하지 않습니다. |

설정을 바꾸면 `make api-reload`로 API를 다시 읽힙니다.

## 4. Registry 연결 (B Adapter 이후)

`create_app(wallet_chain=...)`에 `originproof_core.wallet_ports.WalletRegistry`를 구현한 객체를 넘깁니다. 반환 증거의 `chain_id`·`verifying_contract`가 현재 domain과 다르면 API가 503으로 거부합니다. 연결 뒤에는 `/v3` 흐름을 [화면 순서](../api/v5_c_runtime.md#a-화면에서-사용할-순서)대로 확인합니다.

## 5. 검사

```sh
PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src \
  .venv/bin/python -m pytest -q apps/api/tests/test_wallet_runtime.py apps/api/tests/test_wallet_recovery_guards.py apps/api/tests/test_wallet_analyses.py
```

실제 PostgreSQL·프로세스 복구 검사와 독립 RPC 검증 도구는 W6(#63, `phase/W6`에서 병합 예정)에서 다룹니다. 합성 Registry 결과를 실제 체인 연결 성공으로 보고하지 않습니다.

## 6. health 판정과 완료 기준

`/health/live`는 프로세스가 떠 있으면 200입니다. `/health/ready`는 v5 전용 검사가 아니라 P0 전체 준비 상태(`readiness.py`)를 봅니다. migration head, `operator`·`recipient`·`issuer` 역할 계정, `API_FINALS_*_ISSUER_ID` 두 기관의 issuer 계정, 체인 조회, projection 동기화가 모두 맞아야 200입니다.

| 준비한 것 | `/health/ready` | 이유 |
| --- | --- | --- |
| `mvp-up`·`db-upgrade`·`v5-wallet-seed`만 | **503 (정상)** | v5 계정에는 `recipient`와 finals 기관 issuer가 없습니다 |
| 1절 `make finals-up` + `v5-wallet-seed`, `API_WALLET_REGISTRY_ADDRESS` 비움 | 200 | 기존 P0 계정·legacy 체인(Anvil)·projection으로 판정합니다. `finals-up`이 마지막에 이 200을 확인하며, Registry 주소를 넣은 `.env`로 실행하면 이 단계에서 실패합니다 |
| `API_WALLET_REGISTRY_ADDRESS` 설정, Registry 미주입 | **503 (현재 한계)** | 각 기관을 Registry로 조회하는데 `wallet_chain=None`이라 실패합니다. B Adapter 연결(4절) 뒤 200이 됩니다 |

이 runbook 단계(합성 계정·설정)의 완료 기준은 다음과 같습니다. ready 200은 위 둘째 줄 조건에서만 기대합니다.

1. `make v5-wallet-seed`를 두 번 실행해 같은 계정 ID와 같은 설정 두 줄이 나오고, 기존 계정이 바뀌지 않습니다.
2. 출력값을 `.env`에 넣고 `make api-reload` 한 뒤 API 설정에 그대로 반영됩니다.
3. `/health/live`가 200입니다.

2026-10-21 D 독립 실행(격리 PostgreSQL)에서 1~3과 seed만 한 상태의 ready 503을 확인했습니다. 둘째 줄은 기존 `finals-up`의 ready 확인에 기댄 설명이며, v5 seed를 더한 조합은 이 PR에서 실행하지 않았습니다.
