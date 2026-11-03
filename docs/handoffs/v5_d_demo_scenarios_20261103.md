# D 발표 시나리오·AI 기대 결과 초안

2026-11-03 · V5-W7-D 준비 · D 여인준 `@yijun0330`. 사용자 지시로 Codex가 기존 자료/실행 근거를 대조해 작성했습니다. **팀 선택 전 초안**, 실제 모델 실행 승인·발표 순서/장비 확정·최종 RC 수용이 아닙니다.

관련 결정은 [#117](https://github.com/OriginProof-3web/OriginProof/issues/117)에서 합의합니다. [최종 검증·리허설 작업표](../qa/v5-d-final-rc-workbook.md)와 연결합니다. 최종 RC SHA·manifest·발표 데이터는 C가 지정합니다. W7 phase가 없어 최신 integration에서 작성한 준비 문서이며 W6 기능을 integration에 승격하는 PR이 아닙니다.

## 준비된 원본과 보존 기준

- 재사용 소스: `0466633576e7e5ce6a0ec3eee5ba5ba5581ab0fd`의 [검토된 합성60개](https://github.com/OriginProof-3web/OriginProof/blob/0466633576e7e5ce6a0ec3eee5ba5ba5581ab0fd/fixtures/synthetic/phishing_sources_v1.json), SHA256 `3c3b0c66fd3c4f851dce01255855f6a5db5f28397f9ade20469ec27918522199`.
- **개발 자료만** 제안에 사용합니다. 보류 평가36개·라벨·분할·원본/이미지를 바꾸거나 새 독립 평가로 재사용하지 않습니다.
- TEXT·DOCUMENT_IMAGE만 대상입니다. PDF·음성·Decisions·Jev를 추가하지 않습니다. gpt-6-luna 선택은 유지합니다.
- 과거 텍스트/이미지 실측과 현재 규칙0.2를 구분합니다. 과거 성능 수치를 현행 새 후보 실측으로 승계하지 않습니다.
- 모델 결과는 아래 기대와 다를 수 있습니다. 근거 원문 대조·보류/실패 표시를 지키며 실제 결과를 그대로 기록합니다. 재시도로 좋은 결과만 고르지 않습니다.

## 1. 회의에서 선택할 후보 7개

필수 수용 기능을 모두 발표 장면에 넣으라는 뜻은 아닙니다. 제한된 발표에서 선택한 장면 외 기능은 전체 영상/수용표로 증명합니다.

| ID | 입력 준비 | 발행·내용·현재 상태 기대 | AI 기대·현재 경로 | 준비 상태 |
| --- | --- | --- | --- | --- |
| S01 정상 최신본 | 최종 RC의 `verify-samples.txt` **J1**, v2 보호 필드 | VERIFIED / FULL_COMPARISON / ACTIVE. 보호 필드 비교이며 받은 파일 bytes 비교와 구분 | 검증 JSON 경로는 현재 AI 요청을 하지 않음. NOT_RUN을 “AI 안전”으로 설명하지 않음 | 로컬 사전 검증 재사용 가능, 최종 데이터 고정 필요 |
| S02 금액1원 변조 | **J2**, S01에서 amount_minor만+1 | TAMPERED, 내용 불일치. 발행 기록 존재와 받은 필드 일치를 구분 | 검증만 실행. 낮은 AI 위험이 불일치를 지우지 않는 조합은 별도 연결 확인 | 로컬 사전 검증 재사용 가능 |
| S03 구버전 | **J3**, 같은 문서 v1 | VERIFIED / SUPERSEDED. 과거 발행 확인과 현재 사용 가능 상태를 구분 | 검증만 실행 | 로컬 사전 검증 재사용 가능 |
| S04 철회 | C가 별도로 준비한 철회 문서의 정확한 입력 | 정상 서명/내용 여부와 REVOKED 현재 상태를 분리. 과거 버전 자동 활성화 없음 | 검증만 실행 | 최종 dataset/입력 대기. S01 문서를 임의 철회하지 않음 |
| S05 미등록·위험 지시 | 문서 미등록은 **J5**, 위험 지시는 아래 T-H03/T-K10 | J5는 NOT_REGISTERED. “사기 확정”과 구분 | 위험 TEXT는 HIGH/RULE 근거 기대. 두 독립 입력을 하나의 결합 결과로 소개하지 않음 | 개별 경로 준비. 결합 보고서를 선택하면 A/C 연결 확인 필요 |
| S06 문서 이미지 | 아래 I-H03 PNG | 이미지 단독은 발행 검증 미실행. 문서 ID/내용 연결 여부를 별도 표시 | 판독→사용자 확인→원문 근거 대조. 원문이 유지되면 REMOTE_CONTROL_REQUEST 기대 | 개발 이미지 준비. 최종 업로드/모델 사전 확인은 C 범위 승인 뒤 |
| S07 코드 없는 문자 | 최종 발행 원문에서 Proof/문서ID가 없는 정확한 문자, C 제공 | 후보0/1/여러 개·보호 필드 범위를 구분. 단순 후보 조회를 원본 bytes 일치로 표시하지 않음 | AI 결과가 발행 진위를 결정하지 않음 | 정확한 입력/후보 개수/검색 키를 dataset과 함께 고정해야 함 |

S01~S03의 J1~J3·J5는 [C 실행 보조 고정본](https://github.com/OriginProof-3web/OriginProof/blob/4b3f1289b53f2cf88d53f2bac03082c3ec26fbe6/scripts/rc_local.sh)의 생성 경로를 재사용합니다. 임의 document_id·서명을 문서에 박아 넣지 않습니다. 최종 RC가 만드는 입력 파일의 hash와 문서/버전/chain/Registry를 실행 기록에 연결합니다.

## 2. D가 준비한 정확한 TEXT 후보

### T-H03 — 개발 DP-H03 재사용

```text
Origin Mock Office 점검을 위해 원격제어 앱을 설치해 주세요.
```

규칙 기대: HIGH / REMOTE_CONTROL_REQUEST. 현재 mock도 모델 성공을 만들지 않고 RULE 근거와 `LLM_ANALYSIS_UNAVAILABLE`를 함께 설명합니다. 문서 ID가 없는 이 TEXT만으로 NOT_REGISTERED라고 판정하지 않습니다. 발행 검증은 미실행입니다.

### T-K10 — 이미 추가된 K10 회귀의 최소 입력

```text
아래 링크에서 원격지원 앱을 설치하고 본인 계좌 비밀번호를 입력해 주세요.
```

규칙0.2 기대: HIGH, REMOTE_CONTROL_REQUEST와 CREDENTIAL_REQUEST. 두 근거의 원문/Unicode 위치가 유효해야 합니다. 실제 OpenAI 결과와 RULE/LLM 출처·사용 불가/fallback 표시를 분리합니다.

### T-N01 — 개발 DP-N01 경고 문맥

```text
Origin Mock Bank는 문자나 전화로 인증번호를 요청하지 않습니다. 공식 앱에서 안내를 확인하세요.
```

규칙 기대: NO_CLEAR_INDICATORS/요청 근거0. **기본 mock pipeline**은 모델 사용 불가 때문에 UNDETERMINED일 수 있습니다. 실제 모델의 기대 수준은 NO_CLEAR_INDICATORS이나 안전 보장이 아닙니다. 경고 문맥의 단어를 위험 요청으로 오탐하지 않는지 확인합니다.

## 3. IMAGE와 예비 실패 사례

| ID | 고정 파일/원문 | SHA256 | 기대·한계 |
| --- | --- | --- | --- |
| I-H03 | [DP-H03.png](https://github.com/OriginProof-3web/OriginProof/blob/0466633576e7e5ce6a0ec3eee5ba5ba5581ab0fd/fixtures/synthetic/selected_input_development_v1/images/DP-H03.png), 원문=T-H03 | `ae9b4b75a772c91f5ddac2b6cb0621354176a4055f541df257a5d2a0309e997e` | 판독문/근거 대조 후 원격제어 요청. mock에서 실제 OCR 성공을 주장하지 않음 |
| I-C04 예비 | [DP-C04.png](https://github.com/OriginProof-3web/OriginProof/blob/0466633576e7e5ce6a0ec3eee5ba5ba5581ab0fd/fixtures/synthetic/selected_input_development_v1/images/DP-C04.png), “처음 보는 관리자가 업무용이라고 설명하며 일반 앱 설치 파일을 보내왔습니다.” | `b7cb53472b18d516d1985d62ed37fc271a06fd555fd9ff491be95cbf432e294d` | 라벨CAUTION, 과거 이미지 실측UNDETERMINED/문자완전일치. 알려진 한계로 보존·C 동의, A 품질/표시 확인 후 사용 |
| I-U03 예비 | [DP-U03.png](https://github.com/OriginProof-3web/OriginProof/blob/0466633576e7e5ce6a0ec3eee5ba5ba5581ab0fd/fixtures/synthetic/selected_input_development_v1/images/DP-U03.png), `???? …` | `ab7a0f94d2e08efdb27b1a4c7f1fc3d7251d996c06e07c710cff6f53b913e7b9` | UNDETERMINED. 과거 판독8자/edit3, 원문6자. “안전”으로 설명하지 않고 raw 출력은 재구성하지 않음 |

I-C04/I-U03은 재평가하거나 합격선을 바꿀 항목이 아닙니다. 사람의 가독성/경고 수용과 실제 결과 표시의 점검 자료입니다. 사진은 지원 PNG/JPEG/WebP·서버/현재 웹 제한을 최종 RC 기준으로 확인하며 업로드 화면의 안내만으로 수용하지 않습니다.

## 4. 시나리오별 기록 형식

각 선택한 시나리오에 다음을 한 줄씩 채웁니다. 미선택 시나리오는 SKIP_BY_TEAM_SELECTION로 이유를 기록하고 제품 필수 수용 범위에서 조용히 삭제하지 않습니다.

| 필드 | 현재 값/채울 내용 |
| --- | --- |
| selected / order | 미정 |
| RC SHA / manifest / input file SHA256 | 미정, C가 확정한 동일 dataset 사용 |
| input route | TEXT / DOCUMENT_IMAGE / verification JSON / Track B를 구분 |
| expected verification / AI / source | 위 후보에서 선택, AI NOT_RUN/UNAVAILABLE도 별도 |
| actual / elapsed / error_code | 미실행. RULE/LLM·표시 원문 근거·발행/현재 상태 각각 기록 |
| model / prompt / rule version | gpt-6-luna / 해당 RC의 prompt / 현재 규칙0.2와 실제 소스hash 기록 |
| fallback / operator / evidence URL | 팀 결정 후 입력. 좋은 결과만 선택하거나 mock을 실제 AI로 바꿔 쓰지 않음 |

## 5. 장애 대체와 회의 결정

- **AI 실패:** 발행 검증이 성공했다면 그 사실은 남기고 AI는 사용 불가/보류로 표시합니다. 미실행 근거/위험 확률을 만들어내지 않습니다.
- **RPC 실패:** 현재 유효 여부를 보류하고 캐시나 AI 점수로 대신 성공시키지 않습니다.
- **영상/mock 전환:** 진행자가 전환 사실과 녹화본의 RC/데이터 버전을 말합니다. 전환 시점·시간 한도·예비 장비는 팀이 정합니다.
- 기존 최종 텍스트36개를 튜닝/재평가용으로 돌리지 않습니다. C가 #117의 정확한 선택 입력을 실제 모델로 반복 확인할 경우 키/호출 수/출력 상한·예산은 그 범위의 별도 승인으로 진행합니다. 이 문서 작성의 추가 유료0입니다.

회의에서 확정할 것: 선택/순서·정확한 입력·발표 장비/시간·Anvil/Sepolia의 보여 줄 범위·K1/K7 버튼 처리·장애 전환·C 실제 AI 사전 확인 범위. A는 화면/버튼, C는 dataset/실행, D는 AI 기대·근거/한계 기록을 맡습니다.

## 6. 검증된 준비와 아직 하지 않은 일

D가 작성한 초안의 TEXT·개발 split·이미지hash는 고정 Git 원본과 대조했습니다. [W6 사전 실행 증거](https://github.com/OriginProof-3web/OriginProof/blob/7f1e93793fea0ce6c28ade15a741a7bdb5b1ad54/docs/qa/v5-d-closeout-20261103.md)는 별도이며 이 W7 문서 작성으로 새 기능/모델 검사를 실행한 것으로 계산하지 않습니다.

현재 검증 JSON은 AI 요청을 하지 않고 TEXT 분석의 verification_session_id는 null입니다. 결합 시연/최종 V5-F16은 A/C 연결 근거가 필요합니다. 팀 선택·사람 이미지 수용·최종 RC·실제 다른 장비·전체 리허설·제출은 미완료입니다.

## 7. D 설명·영상 자막 문안 초안

장면/발표 시간을 확정하기 전 사용할 문안입니다. 화면의 실제 결과·실행 모드와 맞는 문장만 선택합니다. 발표 길이·성공 결과를 미리 확정하지 않습니다.

| 장면 | 설명 문안 |
| --- | --- |
| 결과 읽기 | “기관 발행 기록, 받은 내용의 비교, 현재 상태를 나눠 확인합니다. 문서 ID만 조회한 경우에는 받은 내용이 같다는 뜻이 아닙니다.” |
| AI 역할 | “AI는 문자의 위험 정황과 근거를 설명합니다. 기관이 발행했는지 결정하거나 발행 검증 결과를 뒤집는 역할은 아닙니다.” |
| 변조·구버전 | “발행 기록이 있어도 받은 필드가 다르면 불일치입니다. 과거 정상 발행된 문서여도 새 버전이 있거나 철회됐다면 현재 상태를 별도로 봅니다.” |
| mock/fallback | “이 장면은 규칙 검사 또는 기록 응답입니다. 실제 모델 품질이나 사진 판독 성공을 보여 준 것이 아닙니다.” — 해당 모드일 때만 |
| AI 실패 | “발행 검증과 AI 분석은 독립입니다. 지금 AI가 완료되지 않았으므로 위험 수준을 성공한 분석처럼 설명하지 않습니다.” |
| RPC 실패 | “현재 체인 상태를 확인하지 못해 사용 가능 여부를 보류합니다. AI 점수나 캐시로 현재 유효 상태를 대신 확정하지 않습니다.” |
| 성능 | “이 사전 측정은 로컬 납부 문서의 HTTP·DB·Anvil 검증100회입니다. p95 약43ms이며 AI·브라우저 시간이나 운영 부하 성능은 포함하지 않습니다.” |

평가 수치를 쓰면 [과거 텍스트 최종36개](https://github.com/OriginProof-3web/OriginProof/blob/0466633576e7e5ce6a0ec3eee5ba5ba5581ab0fd/docs/qa/v5-d-live-holdout-20261027.md)의33/36·macro-F1 0.9118421053과 [개발 이미지23개](https://github.com/OriginProof-3web/OriginProof/blob/0466633576e7e5ce6a0ec3eee5ba5ba5581ab0fd/docs/qa/v5-d-live-images-20261030.md)의22/23을 출처/분할/실행 버전과 함께 설명합니다. 개발 이미지 정확도를 독립 최종 성능으로, 과거 평가를 현재 규칙0.2의 새 측정으로, 합성 소표본을 실제 사용자 탐지율로 소개하지 않습니다.

녹화 시에는 선택한 시나리오의 입력 hash·RC·manifest·실제/mock 모드·실패/전환 사실을 기록하고 비밀값/쿠키/키/비밀번호 화면은 포함하지 않습니다. 최종 RC·시나리오가 없는 지금은 이 문안을 최종 영상이나 제출 완료로 세지 않습니다.
