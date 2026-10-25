# D 입력·평가 A/C 검토본 — 2026-10-25

텍스트·이미지(문서)·음성 선택, gpt-6-luna 유지. 음성 코덱/전사 모델은 미정입니다.
텍스트 평가 우선, PDF 파일은 미선정입니다.
개발24/최종36 제안은 A/C가 수정 없이 확인했습니다.
유료 정책은 별도이며 기본 비승인입니다. 이 생성기는 실제 호출·승인을 하지 않습니다.
180은 세 형식 매핑 수이며 독립 원본/제작/변환/실제 평가 완료 수가 아닙니다.
paid/model flag는 export 준비 범위입니다. 실제 텍스트 평가 이력은 별도 보고서입니다.
텍스트 위치는 Unicode 코드 포인트 [start,end)이며 이미지 영역·음성 시간으로 복사하지 않습니다.
아래 D 판단 근거·flags·분할 관계는 검토 전 제안 이력으로 보존합니다.

- A 확인: https://github.com/OriginProof-3web/OriginProof/pull/94#issuecomment-6381593781
- C 확인: https://github.com/OriginProof-3web/OriginProof/pull/94#issuecomment-6380482888
- H01/H11 문구 공유: 분할 유지. 최종 H11 결과 별도 표시(현재 예측 없음).
- H08 추가 인용 권고는 미적용했습니다. 기존 라벨·원문·인용·분할을 보존합니다.
- U05/U13/U15는 텍스트 사례이며 실제 OCR/STT 실패 수로 합산하지 않습니다.

개발 이미지 23개, 대본 22개. 정식 녹음/변환 평가0.
[이미지/녹음 계획 manifest](../../fixtures/synthetic/selected_input_development_v1/manifest.json)

별도 로컬 TTS 초안 13개. 사람 검토/실제 STT 평가0.

## 분할 관계 기록

- DP-H01, DP-H11, DP-N15: 같은 인증번호 공유 문구의 요청/자칭 예방/거절 대비가 양쪽 분할에 있습니다. 실제 원본의 변형인지 A/C가 확인한 후 source_group/분할을 고정해야 합니다.
- DP-H03, DP-N08, DP-N11: 원격제어 설치 요청과 예방/부정 문맥의 대비가 양쪽 분할에 있습니다. 의도된 대조 사례와 파생 원본 관계를 검토해야 합니다.
- DP-H04, DP-N03, DP-H12, DP-H14: 긴급 송금·피해 위협의 유사 틀이 있습니다. 같은 사례의 변형인지 확정하지 않고 분할 독립성 리뷰 대상으로 남깁니다.

## 사례별 검토

### DP-H01 · development · HIGH

> Origin Mock Bank 보안팀입니다. 본인 확인을 위해 인증번호를 알려주세요.

- D 판단 근거: 보안팀을 자칭하며 인증번호를 타인에게 알려 달라고 직접 요청합니다.
- 원래 flag: 없음
- 인용 [35,46): 인증번호를 알려주세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-H02 · development · HIGH

> 계정이 도용되었습니다. OTP를 보내주세요. 상담원이 대신 처리합니다.

- D 판단 근거: 도용을 구실로 OTP 전달을 요구하고 상담원이 대신 처리한다고 설명합니다.
- 원래 flag: 없음
- 인용 [13,23): OTP를 보내주세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-H03 · development · HIGH

> Origin Mock Office 점검을 위해 원격제어 앱을 설치해 주세요.

- D 판단 근거: 기관 점검을 명분으로 원격제어 앱 설치를 직접 요구합니다.
- 원래 flag: 없음
- 인용 [26,41): 원격제어 앱을 설치해 주세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-H04 · development · HIGH

> 수사 협조 대상입니다. 지금 아래 계좌로 송금하세요.

- D 판단 근거: 수사 협조를 명분으로 즉시 송금을 요구합니다.
- 원래 flag: 없음
- 인용 [13,28): 지금 아래 계좌로 송금하세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-H05 · development · HIGH

> 본인 보호 절차입니다. 은행에 확인하지 마세요. 조사 내용은 비밀입니다.

- D 판단 근거: 은행의 독립 확인을 막고 비밀 유지를 요구합니다. 금전·비밀정보 요청이 없어 HIGH/CAUTION 경계를 리뷰해야 합니다.
- 원래 flag: LABEL_BOUNDARY_REVIEW
- 인용 [13,25): 은행에 확인하지 마세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-H06 · development · HIGH

> 청구 계좌가 바뀌었습니다. 즉시 변경된 계좌로 입금해 주세요.

- D 판단 근거: 계좌 변경과 즉시 입금 요청이 결합돼 있습니다.
- 원래 flag: 없음
- 인용 [15,33): 즉시 변경된 계좌로 입금해 주세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-H07 · holdout · HIGH

> 위험한 상황이니 가족에게 연락하지 마세요. 저희 지시만 따르면 됩니다.

- D 판단 근거: 가족 연락을 막고 지시에 따르도록 통제합니다. 구체적 피해 행동이 없어 HIGH/CAUTION 경계를 리뷰해야 합니다.
- 원래 flag: LABEL_BOUNDARY_REVIEW
- 인용 [9,22): 가족에게 연락하지 마세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-H08 · holdout · HIGH

> 보안 재설정 링크 화면에 인증번호를 입력하세요. 기존 창구는 이용하지 마세요.

- D 판단 근거: 보안 화면에 인증번호 입력과 기존 창구 회피를 함께 요구합니다. 인증번호 입력만으로 악성이라 단정할 수 없어 문맥을 함께 검토해야 합니다.
- 원래 flag: LABEL_BOUNDARY_REVIEW, EVIDENCE_CONTEXT_REVIEW
- 인용 [14,25): 인증번호를 입력하세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-H09 · holdout · HIGH

> 환급을 받으려면 보안카드 번호를 전달해 주세요. 상담원이 등록합니다.

- D 판단 근거: 환급을 명분으로 보안카드 번호 전달을 직접 요구합니다.
- 원래 flag: 없음
- 인용 [9,25): 보안카드 번호를 전달해 주세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-H10 · holdout · HIGH

> 검사를 위해 비밀번호를 공유해 주세요. 귀하의 계정을 저희가 점검합니다.

- D 판단 근거: 계정 점검을 명분으로 비밀번호 공유를 직접 요구합니다.
- 원래 flag: 없음
- 인용 [7,20): 비밀번호를 공유해 주세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-H11 · holdout · HIGH

> 피싱 예방팀입니다. 안전 조치를 위해 인증번호를 알려주세요.

- D 판단 근거: 피싱 예방팀을 자칭하지만 실제 요청은 인증번호 공유입니다. 예방이라는 단어만으로 예외 처리하지 않습니다.
- 원래 flag: 없음
- 인용 [21,32): 인증번호를 알려주세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-H12 · holdout · HIGH

> 중복 결제를 막으려면 3분 이내 임시 계좌로 이체해 주세요.

- D 판단 근거: 중복 결제 방지를 구실로 3분 이내 임시 계좌 이체를 요구합니다.
- 원래 flag: 없음
- 인용 [12,32): 3분 이내 임시 계좌로 이체해 주세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-H13 · holdout · HIGH

> 새 보안 절차입니다. OTP를 이 대화로 전송해 주세요. 직접 로그인하지 마세요.

- D 판단 근거: OTP를 대화로 전송하도록 요구하며 정상 로그인 경로를 피하게 합니다.
- 원래 flag: 없음
- 인용 [12,30): OTP를 이 대화로 전송해 주세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-H14 · holdout · HIGH

> 압류를 막으려면 당장 안전 계좌로 입금하세요.

- D 판단 근거: 압류를 명분으로 당장 안전 계좌에 입금하라고 요구합니다.
- 원래 flag: 없음
- 인용 [9,24): 당장 안전 계좌로 입금하세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-H15 · holdout · HIGH

> 원격 지원 프로그램을 실행해 주세요. 이후 계정 비밀값을 상담원에게 보내야 합니다.

- D 판단 근거: 원격 지원 프로그램 실행과 상담원에게 계정 비밀값 전달을 요구합니다.
- 원래 flag: 없음
- 인용 [0,19): 원격 지원 프로그램을 실행해 주세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C01 · development · CAUTION

> 안내드립니다. 변경된 계좌로 입금해 주세요. 변경 사유와 담당자는 적혀 있지 않습니다.

- D 판단 근거: 담당자·사유 없는 변경 계좌 입금 요청입니다. 긴급성이나 비밀값 요청은 명시되지 않았습니다.
- 원래 flag: 없음
- 인용 [8,23): 변경된 계좌로 입금해 주세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C02 · development · CAUTION

> 신청한 기억이 없는 환급 안내가 왔습니다. https://refund.example.invalid 에서 접수하라고 합니다.

- D 판단 근거: 신청 기억이 없는 환급과 링크 접수가 결합됩니다. URL 모양만으로 악성 여부를 확정하지 않습니다.
- 원래 flag: 없음
- 인용 [24,67): https://refund.example.invalid 에서 접수하라고 합니다
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C03 · development · CAUTION

> 알 수 없는 발신자가 서류 확인을 위해 링크에 이름과 생년월일을 입력해 달라고 합니다.

- D 판단 근거: 알 수 없는 발신자가 이름·생년월일을 링크에 입력하도록 요청합니다. 불완전한 신원정보 수집 문맥입니다.
- 원래 flag: 없음
- 인용 [26,47): 이름과 생년월일을 입력해 달라고 합니다
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C04 · development · CAUTION

> 처음 보는 관리자가 업무용이라고 설명하며 일반 앱 설치 파일을 보내왔습니다.

- D 판단 근거: 처음 보는 관리자가 별도 앱 설치 파일을 보냅니다. 원격제어나 실행 요구는 확정되지 않았습니다.
- 원래 flag: 없음
- 인용 [23,41): 일반 앱 설치 파일을 보내왔습니다
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C05 · development · CAUTION

> 기존 안내와 계좌가 다른 납부 문서를 받았습니다. 실제 변경 승인 여부는 확인되지 않았습니다.

- D 판단 근거: 기존과 다른 계좌 및 변경 승인 미확인이 구체적 우려입니다. 실제 계좌 검증 결과는 주어지지 않았습니다.
- 원래 flag: 없음
- 인용 [0,19): 기존 안내와 계좌가 다른 납부 문서
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C06 · development · CAUTION

> Origin Mock Office를 사칭하는지 알 수 없는 계정이 개인 대화로 수수료 납부를 요구합니다.

- D 판단 근거: 기관 관련 불명확한 계정이 개인 대화에서 수수료 납부를 요구합니다.
- 원래 flag: 없음
- 인용 [37,57): 개인 대화로 수수료 납부를 요구합니다
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C07 · holdout · CAUTION

> 요청하지 않은 배송 문자에 주소 변경용 짧은 링크가 포함되어 있습니다. 물품 주문 여부는 불명확합니다.

- D 판단 근거: 요청하지 않은 배송과 주소 변경 링크가 있으나 실제 주문/변경 요청은 불명확합니다.
- 원래 flag: 없음
- 인용 [15,27): 주소 변경용 짧은 링크
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C08 · holdout · CAUTION

> 수신자 이름이 없는 신규 청구서가 도착했고 추가 납부를 요청합니다. 청구 근거가 없습니다.

- D 판단 근거: 수신자·청구 근거가 없는 신규 추가 납부 요청입니다.
- 원래 flag: 없음
- 인용 [24,36): 추가 납부를 요청합니다
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C09 · holdout · CAUTION

> 기존 거래처와 비슷한 이름의 계정에서 새 계좌로 송금해 주세요라는 요청을 받았습니다.

- D 판단 근거: 거래처와 비슷한 이름의 계정 및 새 계좌 송금 요청이 결합됩니다.
- 원래 flag: 없음
- 인용 [21,34): 새 계좌로 송금해 주세요
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C10 · holdout · CAUTION

> 교육 등록 안내에 낯선 외부 사이트에서 신분 정보 제출을 요청하는 문구가 있습니다.

- D 판단 근거: 낯선 외부 사이트에서 신분정보 제출을 요청합니다. 제출할 정보와 목적이 불완전합니다.
- 원래 flag: 없음
- 인용 [22,39): 신분 정보 제출을 요청하는 문구
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C11 · holdout · CAUTION

> 확인되지 않은 QR 안내가 별도 로그인 화면으로 연결된다고 설명합니다. 실제 페이지는 방문하지 않았습니다.

- D 판단 근거: 미확인 QR의 별도 로그인 화면 연결 설명입니다. QR/로그인 자체는 악성이 아니므로 CAUTION/UNDETERMINED 경계 리뷰가 필요합니다.
- 원래 flag: LABEL_BOUNDARY_REVIEW
- 인용 [15,38): 별도 로그인 화면으로 연결된다고 설명합니다
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C12 · holdout · CAUTION

> 기관 직원을 자칭한 메시지가 개인 명의 계좌로 보증금을 보내 달라고 합니다.

- D 판단 근거: 기관 직원을 자칭하며 개인 명의 계좌에 보증금을 보내 달라고 요구합니다.
- 원래 flag: 없음
- 인용 [16,41): 개인 명의 계좌로 보증금을 보내 달라고 합니다
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C13 · holdout · CAUTION

> 채용 안내가 합격 사실을 알리며 업무 시작 전 장비 비용 선납을 요구합니다. 채용 내역은 불명확합니다.

- D 판단 근거: 불명확한 채용에서 업무 전 장비 비용 선납을 요구합니다.
- 원래 flag: 없음
- 인용 [26,41): 장비 비용 선납을 요구합니다
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C14 · holdout · CAUTION

> 청구 담당자 변경 안내와 함께 암호가 걸린 첨부 파일을 받았습니다. 발신 경로가 확인되지 않았습니다.

- D 판단 근거: 발신 경로가 확인되지 않은 암호화 첨부입니다. 암호화만으로 의심을 높이지 않도록 CAUTION/NO_CLEAR_INDICATORS 경계를 리뷰해야 합니다.
- 원래 flag: LABEL_BOUNDARY_REVIEW
- 인용 [17,29): 암호가 걸린 첨부 파일
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-C15 · holdout · CAUTION

> 사용하지 않는 서비스가 이용료가 밀렸다고 안내합니다. 금액과 계약 정보는 없고 문의 채널이 개인 계정입니다.

- D 판단 근거: 미사용 서비스의 미납 주장에 금액·계약 정보가 없고 개인 문의 채널을 안내합니다.
- 원래 flag: 없음
- 인용 [44,59): 문의 채널이 개인 계정입니다
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N01 · development · NO_CLEAR_INDICATORS

> Origin Mock Bank는 문자나 전화로 인증번호를 요청하지 않습니다. 공식 앱에서 안내를 확인하세요.

- D 판단 근거: 기관을 자칭하지만 인증번호를 요청하지 않는다는 부정문과 공식 앱 확인 안내입니다. 발행 진위는 판단하지 않습니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N02 · development · NO_CLEAR_INDICATORS

> 합성 시설의 정기 점검은 다음 주 화요일입니다. 점검 중 일부 조회가 지연될 수 있습니다.

- D 판단 근거: 시설 점검 일정과 조회 지연의 단순 안내로 위험 행동 요청이 없습니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N03 · development · NO_CLEAR_INDICATORS

> 사기 예방 예시: "지금 아래 계좌로 송금하세요"라는 문구를 받으면 응하지 말고 공식 창구에서 확인하세요.

- D 판단 근거: 송금 요구가 인용된 예방 예시이고 응하지 말라는 거절 문맥이 명시됩니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N04 · development · NO_CLEAR_INDICATORS

> Origin Mock Office의 신청 문서는 방문 창구에서 수령할 수 있습니다. 신분 확인은 현장에서 진행합니다.

- D 판단 근거: 방문 수령과 현장 신분 확인 안내입니다. 메시지로 비밀정보를 수집하는 요구는 없습니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N05 · development · NO_CLEAR_INDICATORS

> 이미 처리된 신청이며 추가 납부는 없습니다. 이번 안내는 진행 상태를 알려드리는 문서입니다.

- D 판단 근거: 추가 납부가 없음을 명시한 진행 상태 안내입니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N06 · development · NO_CLEAR_INDICATORS

> 인증번호나 비밀번호를 누구에게도 알려주지 마세요. 의심되면 기존 공식 연락처를 직접 찾아 확인하세요.

- D 판단 근거: 인증번호·비밀번호 공유 금지와 기존 공식 연락처 확인을 권고합니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N07 · holdout · NO_CLEAR_INDICATORS

> 사무실 휴관일은 주말입니다. 다음 영업일에 정상 운영합니다.

- D 판단 근거: 휴관일과 영업일 안내로 금전·비밀정보 요구가 없습니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N08 · holdout · NO_CLEAR_INDICATORS

> 피싱 교육 사례: ‘원격제어 앱을 설치해 주세요’는 사기 예시입니다. 이런 설치 요구를 거절하세요.

- D 판단 근거: 원격제어 설치 요구는 교육 사례로 인용되고 실제로는 거절하도록 안내합니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N09 · holdout · NO_CLEAR_INDICATORS

> Origin Mock Office 안내 문서의 제목 오탈자를 정정했습니다. 내용 변경 이력은 문서 목록에서 확인하세요.

- D 판단 근거: 제목 오탈자와 문서 변경 이력 확인 안내입니다. 기록의 실제 진위를 입증하는 자료는 아닙니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N10 · holdout · NO_CLEAR_INDICATORS

> 예약 일정이 금요일 오후로 변경되었습니다. 비용이나 로그인 정보 제출은 요청하지 않습니다.

- D 판단 근거: 예약 일정 변경이며 비용·로그인 정보 제출을 요청하지 않는다고 명시합니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N11 · holdout · NO_CLEAR_INDICATORS

> 직원이 원격제어 앱을 설치하라고 하더라도 설치하지 마세요. 개인정보를 제공하지 마세요.

- D 판단 근거: 직원의 설치 요구에 따르지 말라는 부정문과 개인정보 제공 금지 문맥입니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N12 · holdout · NO_CLEAR_INDICATORS

> 신문 교육란에서 인증번호 탈취와 계좌 변경 사기의 수법을 설명합니다. 실제 송금 요청은 없습니다.

- D 판단 근거: 사기 수법을 설명하는 교육 내용이며 실제 송금 요청이 없다고 명시합니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N13 · holdout · NO_CLEAR_INDICATORS

> 문의는 사용하던 공식 앱의 고객센터 메뉴로 접수하세요. 이 메시지에는 접속 링크가 없습니다.

- D 판단 근거: 기존 공식 앱의 고객센터 메뉴 이용 안내이며 메시지의 외부 링크는 없습니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N14 · holdout · NO_CLEAR_INDICATORS

> 동아리 도서 반납일을 안내합니다. 다음 모임에 대여한 책을 가져와 주세요.

- D 판단 근거: 동아리의 책 반납 요청이며 금전·비밀정보·원격제어 요청이 없습니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-N15 · holdout · NO_CLEAR_INDICATORS

> 공식 경고: "인증번호를 알려주세요"라는 요청은 무시하세요. 은행은 해당 값을 받지 않습니다.

- D 판단 근거: 인증번호 공유 요구를 인용하고 무시하라는 경고입니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U01 · development · UNDETERMINED

> 입금... [이후 내용 누락]

- D 판단 근거: 입금이라는 일부 단어와 누락 표시만 있어 요청/위험을 결정할 문맥이 부족합니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U02 · development · UNDETERMINED

> 1234 5678 90

- D 판단 근거: 숫자열만 있으며 값의 종류나 요청 행동이 없습니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U03 · development · UNDETERMINED

> ???? …

- D 판단 근거: 문장 내용이 없는 기호 조각입니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U04 · development · UNDETERMINED

> 그쪽 번호 먼저 확인하고 보내주세요.

- D 판단 근거: 번호와 전송 대상이 무엇인지 문맥이 없습니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U05 · development · UNDETERMINED

> [합성 판독 불가: 요청 내용 없음]

- D 판단 근거: 판독 불가를 설명하는 합성 표식이며 실제 OCR 실패 입력은 아닙니다.
- 원래 flag: PLACEHOLDER_NOT_MODALITY_TEST
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U06 · development · UNDETERMINED

> 아까 말한 절차대로 진행하시면 됩니다.

- D 판단 근거: 이전 절차를 참조하지만 그 절차의 내용이 없습니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U07 · holdout · UNDETERMINED

> 계좌가 [가려짐]이라 확인할 수 없습니다.

- D 판단 근거: 가려진 계좌를 설명할 뿐 송금 요구와 실제 문맥은 없습니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U08 · holdout · UNDETERMINED

> 발신자와 요청이 모두 누락된 메시지 조각입니다.

- D 판단 근거: 발신자와 요청이 누락됐다는 설명으로 실제 요구를 판단할 수 없습니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U09 · holdout · UNDETERMINED

> 네, 그것을 처리해 주세요.

- D 판단 근거: 대상이 생략된 처리 요청입니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U10 · holdout · UNDETERMINED

> 서로 상충하는 두 안내만 있고 원문은 없습니다.

- D 판단 근거: 서로 상충한다는 설명만 있고 비교할 두 원문이 없습니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U11 · holdout · UNDETERMINED

> 확인했나요?

- D 판단 근거: 무엇을 확인했는지 생략된 질문입니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U12 · holdout · UNDETERMINED

> 링크 부분만 삭제되어 무엇을 요구하는지 알 수 없습니다.

- D 판단 근거: 링크와 요청 문맥이 삭제됐다는 설명만 있습니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U13 · holdout · UNDETERMINED

> [합성 전사 미확보: 분석할 발화 내용 없음]

- D 판단 근거: 전사 미확보를 설명하는 합성 표식이며 실제 STT 실패 입력은 아닙니다.
- 원래 flag: PLACEHOLDER_NOT_MODALITY_TEST
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U14 · holdout · UNDETERMINED

> 수수료는 그때와 같다고 합니다. 어떤 거래인지는 적혀 있지 않습니다.

- D 판단 근거: 수수료와 거래 문맥이 생략됐고 납부 요청도 명확하지 않습니다.
- 원래 flag: 없음
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED

### DP-U15 · holdout · UNDETERMINED

> 사진 속 글자는 읽을 수 없다는 설명만 전달되었습니다.

- D 판단 근거: 사진 글자가 읽히지 않는다는 설명만 있어 실제 이미지 판독 실패 검사가 아닙니다.
- 원래 flag: PLACEHOLDER_NOT_MODALITY_TEST
- 기대 인용 없음
- A: CONFIRMED_UNCHANGED / C: CONFIRMED_UNCHANGED
