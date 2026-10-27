/* 자동 생성 파일: tools/sample_tool.py build 로 data/sample_*.json 에서 만듦. 손으로 고치지 마세요.
   예시 응답(sample)이며 실제 OriginProof API 결과가 아닙니다. */
window.SAMPLE_DATA = [
 {
  "id": "normal",
  "sample": true,
  "label": "예시 응답",
  "button_label": "정상 안내",
  "assumption": "A 화면 실제 결과(금액 변조 검사)의 원래 값 85,000원을 바탕으로 4.1 표 값을 조합한 예시입니다. 블록 번호·서명자 주소는 B 시안의 예시 값입니다.",
  "history": {
   "date": "2026-10-18",
   "title": "카드 결제 예정 금액 안내",
   "tone": "info",
   "icon": "info",
   "label": "기록 일치"
  },
  "input": {
   "kind": "message",
   "text": "[OO카드] 10월 결제 예정 금액은 85,000원입니다. 납부 계좌: OO은행 123-456-789012 (예금주 OO카드). 검증 링크: https://verify.example/p/prf_1b2c3d4e5f60718293a4b5c6d7e8f901",
   "출처": "미확인",
   "메모": "피터가 만든 예시 문자. 기관 이름은 OO로 가림."
  },
  "verification_status": "VERIFIED",
  "conclusion": {
   "badge": {
    "tone": "info",
    "icon": "info",
    "text": "기록 일치"
   },
   "text": "발행 기록·서명·원본이 모두 맞고, 지금도 유효한 안내예요.",
   "출처": "미확인",
   "메모": "결론 문장: 배너 T1-b 제안(2026-10-19)"
  },
  "axes": [
   {
    "axis": "official",
    "name": "공식 발행",
    "status": "확인됨",
    "tone": "ok",
    "icon": "check",
    "body": "등록된 기관이 이 안내문을 발행한 기록이 있고, 서명도 그 기관 것이에요.",
    "staff": [
     "ledger",
     "signature"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "original",
    "name": "원본 일치",
    "status": "일치",
    "tone": "ok",
    "icon": "check",
    "body": "받은 내용이 원본과 한 글자도 다르지 않아요. 금액 85,000원도 원본과 같아요.",
    "staff": [
     "original"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태(금액 문장은 덧붙임)"
   },
   {
    "axis": "status",
    "name": "현재 상태",
    "status": "유효",
    "tone": "ok",
    "icon": "check",
    "body": "지금도 유효한 안내예요.",
    "staff": [
     "status"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "ai",
    "name": "AI 위험",
    "status": "뚜렷한 신호 없음",
    "tone": "info",
    "icon": "info",
    "body": "뚜렷한 위험 신호는 못 찾았어요. 문제가 없다는 뜻은 아니에요.",
    "note": "AI는 설명만 하고 발행 여부를 판정하지 않아요.",
    "staff": [
     "ai"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태, 1.7 근거 보기"
   }
  ],
  "ai_report": {
   "risk_level": "NO_CLEAR_INDICATORS",
   "evidence": [
    {
     "quote": "결제 예정 금액은 85,000원입니다",
     "source": "input.text",
     "start_offset": 11,
     "end_offset": 31,
     "role": "request"
    }
   ],
   "matched_technique_ids": null,
   "출처": "미확인",
   "메모": "T1 예시 근거 위치(피터 작성). 실제 분석기 출력 아님. 수법 ID 는 자리만(목록 연결 전)."
  },
  "next_action": {
   "text": "안내에 적힌 계좌로 돈을 보내기 전에는 기관의 공식 전화번호로 한 번 더 확인하세요.",
   "출처": "웹_설계.md 1.8 보장하지 않는 것 1번을 줄임"
  },
  "details": [
   {
    "label": "검증 엔진 결과",
    "value": "VERIFIED"
   },
   {
    "label": "쉬운 설명",
    "value": "검증 엔진 기준으로 발행 기록·서명·원본이 맞아요. 지금도 유효한지는 '현재 상태' 칸을 보세요."
   },
   {
    "label": "Proof ID",
    "value": "prf_1b2c3d4e5f60718293a4b5c6d7e8f901"
   },
   {
    "label": "checks",
    "value": "issuer=PASS · signature=PASS · payload_hash=PASS · candidate_match=PASS"
   },
   {
    "label": "lifecycle_status",
    "value": "ACTIVE"
   },
   {
    "label": "block_number",
    "value": "6812034 (예시 값)"
   },
   {
    "label": "signer",
    "value": "0x3f9a1c…9e21 (예시 값)"
   },
   {
    "label": "AI",
    "value": "NO_CLEAR_INDICATORS"
   }
  ],
  "staff": [
   {
    "staff": "intake",
    "name": "접수 직원",
    "bubble_key": "intake.fixture",
    "line1": "시연 자료 받음",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 접수 직원"
   },
   {
    "staff": "ledger",
    "name": "블록체인 기록관",
    "bubble_key": "ledger.recorded",
    "line1": "발행 기록 있음",
    "line2": "블록 #6,812,034",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 블록체인 기록관(2줄 블록 번호는 예시 값)"
   },
   {
    "staff": "signature",
    "name": "서명 감정사",
    "bubble_key": "signature.match",
    "line1": "기관 서명과 일치",
    "line2": "서명자 0x3f9a…9e21",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 서명 감정사"
   },
   {
    "staff": "original",
    "name": "원본 대조관",
    "bubble_key": "original.same",
    "line1": "원본 그대로",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 원본 대조관"
   },
   {
    "staff": "status",
    "name": "상태 확인관",
    "bubble_key": "status.active",
    "line1": "현재 유효",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 상태 확인관"
   },
   {
    "staff": "ai",
    "name": "AI 분석가",
    "bubble_key": "ai.no_clear",
    "line1": "뚜렷한 위험 신호는 못 찾았어요",
    "line2": "NO_CLEAR_INDICATORS",
    "shape": "정보",
    "tone": "info",
    "출처": "웹_설계.md 4.1 AI 분석가"
   },
   {
    "staff": "report",
    "name": "보고서 담당",
    "bubble_key": "report.ready",
    "line1": "네 축 보고서를 정리했어요",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 보고서 담당"
   }
  ]
 },
 {
  "id": "tamper",
  "sample": true,
  "label": "예시 응답",
  "button_label": "금액 변조",
  "assumption": "원본 대조 값(85,000원 → 85,001원, TAMPERED · FULL_COMPARISON · AMOUNT_MISMATCH)은 A 화면 실제 결과(docs/디자인_비교/실제-금액변조-검사.png)에서 가져왔습니다. 기록관·감정사·상태 확인관 값은 그 화면에 보이지 않아 B 시안 값으로 채운 예시입니다.",
  "history": {
   "date": "2026-10-18",
   "title": "카드 결제 안내 금액 확인",
   "tone": "fail",
   "icon": "warn",
   "label": "원본과 다름"
  },
  "input": {
   "kind": "message",
   "text": "[OO카드] 10월 결제 예정 금액은 85,001원입니다. 납부 계좌: OO은행 123-456-789012 (예금주 OO카드). 검증 링크: https://verify.example/p/prf_a0ef1f66db9845ebb3ee2fe81c729136",
   "출처": "미확인",
   "메모": "피터가 만든 예시 문자. 금액·Proof ID는 A 실제 결과 화면 값."
  },
  "verification_status": "TAMPERED",
  "conclusion": {
   "badge": {
    "tone": "fail",
    "icon": "warn",
    "text": "원본과 다름"
   },
   "text": "원본과 금액이 달라요. 원본 85,000원, 받은 안내 85,001원이에요.",
   "출처": "미확인",
   "메모": "결론 문장: 배너 T1-b 제안(2026-10-19)"
  },
  "axes": [
   {
    "axis": "official",
    "name": "공식 발행",
    "status": "확인됨",
    "tone": "ok",
    "icon": "check",
    "body": "등록된 기관이 이 안내문을 발행한 기록이 있고, 서명도 그 기관 것이에요.",
    "staff": [
     "ledger",
     "signature"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "original",
    "name": "원본 일치",
    "status": "불일치",
    "tone": "fail",
    "icon": "warn",
    "body": "바뀐 곳: 금액. 원본 85,000원 → 받은 안내 85,001원 (1원 차이)",
    "staff": [
     "original"
    ],
    "compare": [
     {
      "label": "원본 금액",
      "value": "85,000원"
     },
     {
      "label": "받은 안내 금액",
      "value": "85,001원",
      "changed": true
     }
    ],
    "출처": "웹_설계.md 1.8 칸별 상태(원 단위 금액은 덧붙임)"
   },
   {
    "axis": "status",
    "name": "현재 상태",
    "status": "확인 안 함",
    "tone": "none",
    "icon": "dash",
    "body": "앞 단계에서 멈춰 이 항목은 확인하지 않았어요.",
    "staff": [
     "status"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "ai",
    "name": "AI 위험",
    "status": "판단하기 어려움",
    "tone": "pending",
    "icon": "question",
    "body": "AI가 판단하기 어려운 내용이에요. AI 상세 분석 미실행(규칙 검사 결과만)",
    "note": "AI는 설명만 하고 발행 여부를 판정하지 않아요. 금액이 1원 바뀐 것은 원본 대조관만 찾을 수 있어요.",
    "staff": [
     "ai"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태(note 둘째 문장은 덧붙임)"
   }
  ],
  "ai_report": {
   "risk_level": "UNDETERMINED",
   "evidence": [
    {
     "quote": "결제 예정 금액은 85,001원입니다",
     "source": "input.text",
     "start_offset": 11,
     "end_offset": 31,
     "role": "request"
    }
   ],
   "matched_technique_ids": null,
   "출처": "미확인",
   "메모": "T1 예시 근거 위치(피터 작성). 실제 분석기 출력 아님. 수법 ID 는 자리만(목록 연결 전)."
  },
  "next_action": {
   "text": "이 안내의 금액으로 돈을 보내지 마세요. 기관의 공식 전화번호로 원래 금액을 확인하세요.",
   "출처": "미확인",
   "메모": "1.8 보장하지 않는 것 1번을 금액 변조에 맞게 고친 새 문구."
  },
  "details": [
   {
    "label": "검증 엔진 결과",
    "value": "TAMPERED · FULL_COMPARISON · AMOUNT_MISMATCH"
   },
   {
    "label": "쉬운 설명",
    "value": "원본과 다른 곳이 있어요."
   },
   {
    "label": "Proof ID",
    "value": "prf_a0ef1f66db9845ebb3ee2fe81c729136"
   },
   {
    "label": "reason_codes",
    "value": "AMOUNT_MISMATCH"
   },
   {
    "label": "amount_minor",
    "value": "85000 → 85001 (KRW)"
   },
   {
    "label": "합성 발행기관",
    "value": "iss_origin_mock_bank"
   },
   {
    "label": "요청 대상 코드",
    "value": "SYNTHETIC-PAYMENT-001"
   },
   {
    "label": "AI",
    "value": "UNDETERMINED · limitations: LLM_ANALYSIS_UNAVAILABLE"
   }
  ],
  "staff": [
   {
    "staff": "intake",
    "name": "접수 직원",
    "bubble_key": "intake.fixture",
    "line1": "시연 자료 받음",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 접수 직원"
   },
   {
    "staff": "ledger",
    "name": "블록체인 기록관",
    "bubble_key": "ledger.recorded",
    "line1": "발행 기록 있음",
    "line2": "블록 #6,812,034",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 블록체인 기록관(값은 B 시안 예시)"
   },
   {
    "staff": "signature",
    "name": "서명 감정사",
    "bubble_key": "signature.match",
    "line1": "기관 서명과 일치",
    "line2": "서명자 0x3f9a…9e21",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 서명 감정사(값은 B 시안 예시)"
   },
   {
    "staff": "original",
    "name": "원본 대조관",
    "bubble_key": "original.changed",
    "line1": "바뀐 곳: 금액",
    "line2": "AMOUNT_MISMATCH",
    "shape": "경고",
    "tone": "fail",
    "출처": "웹_설계.md 4.1 원본 대조관"
   },
   {
    "staff": "status",
    "name": "상태 확인관",
    "bubble_key": "status.not_run",
    "line1": "앞 단계에서 멈춰 확인 안 함",
    "line2": "",
    "shape": "해당 없음",
    "tone": "none",
    "출처": "웹_설계.md 4.1 상태 확인관"
   },
   {
    "staff": "ai",
    "name": "AI 분석가",
    "bubble_key": "ai.undetermined",
    "line1": "판단하기 어려워요",
    "line2": "UNDETERMINED",
    "line3": "AI 상세 분석 미실행",
    "shape": "보류",
    "tone": "pending",
    "출처": "웹_설계.md 4.1 AI 분석가(덧붙임 행 포함)"
   },
   {
    "staff": "report",
    "name": "보고서 담당",
    "bubble_key": "report.ready",
    "line1": "네 축 보고서를 정리했어요",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 보고서 담당"
   }
  ]
 },
 {
  "id": "impersonation",
  "sample": true,
  "label": "예시",
  "button_label": "사칭 문자",
  "assumption": "A 화면 실제 결과에 없는 경우입니다. 4.1 표 값(ledger.not_found, *.no_source, ai.high)을 조합한 예시입니다.",
  "history": {
   "date": "2026-10-17",
   "title": "카드 정지 본인 확인 문자",
   "tone": "fail",
   "icon": "warn",
   "label": "기록 없음"
  },
  "input": {
   "kind": "message",
   "text": "[OO카드] 고객님 카드가 해외 결제 시도로 정지될 예정입니다. 본인 확인을 위해 아래 링크에서 인증번호를 입력하세요. http://oo-card-check.example/a1",
   "출처": "미확인",
   "메모": "피터가 만든 예시 문자."
  },
  "verification_status": "NOT_REGISTERED",
  "conclusion": {
   "badge": {
    "tone": "fail",
    "icon": "warn",
    "text": "기록 없음"
   },
   "text": "장부에 이 문자의 발행 기록이 없고, 인증번호를 요구하는 문장이 있어요.",
   "출처": "미확인",
   "메모": "결론 문장: 배너 T1-b 제안(2026-10-19)"
  },
  "axes": [
   {
    "axis": "official",
    "name": "공식 발행",
    "status": "기록 없음",
    "tone": "fail",
    "icon": "warn",
    "body": "장부에서 이 기관 또는 이 문서의 발행 기록을 찾지 못했어요.",
    "staff": [
     "ledger",
     "signature"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "original",
    "name": "원본 일치",
    "status": "확인할 원본 없음",
    "tone": "none",
    "icon": "dash",
    "body": "비교할 원본이 없어서 확인하지 않았어요.",
    "staff": [
     "original"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "status",
    "name": "현재 상태",
    "status": "확인할 원본 없음",
    "tone": "none",
    "icon": "dash",
    "body": "비교할 원본이 없어서 지금 상태를 확인하지 않았어요.",
    "staff": [
     "status"
    ],
    "출처": "미확인",
    "메모": "1.8 표에 현재 상태 칸의 '원본 없음' 행이 없어 원본 일치 칸 문구를 고쳐 씀."
   },
   {
    "axis": "ai",
    "name": "AI 위험",
    "status": "위험 신호",
    "tone": "fail",
    "icon": "warn",
    "body": "위험 신호: \"인증번호를 입력하세요\"",
    "note": "AI는 설명만 하고 발행 여부를 판정하지 않아요. 규칙: 인증번호를 요구하는 문장",
    "staff": [
     "ai"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태, 4.1 phishing-rules-0.1"
   }
  ],
  "ai_report": {
   "risk_level": "HIGH",
   "evidence": [
    {
     "quote": "인증번호를 입력하세요",
     "source": "input.text",
     "start_offset": 54,
     "end_offset": 65,
     "role": "risk"
    }
   ],
   "matched_technique_ids": null,
   "출처": "미확인",
   "메모": "T1 예시 근거 위치(피터 작성). 인용 문장은 기존 AI 칸 값과 같음. 수법 ID 는 자리만(목록 연결 전)."
  },
  "next_action": {
   "text": "링크를 누르거나 인증번호를 알려 주지 마세요. 카드 뒷면에 적힌 공식 전화번호로 직접 확인하세요.",
   "출처": "미확인",
   "메모": "새 문구(피터 작성)."
  },
  "details": [
   {
    "label": "검증 엔진 결과",
    "value": "NOT_REGISTERED"
   },
   {
    "label": "쉬운 설명",
    "value": "장부에서 등록된 발행 기록을 찾지 못했어요."
   },
   {
    "label": "reason_codes",
    "value": "PROOF_NOT_FOUND"
   },
   {
    "label": "checks",
    "value": "issuer=NOT_FOUND"
   },
   {
    "label": "AI",
    "value": "HIGH · phishing-rules-0.1 · evidence: \"인증번호를 입력하세요\""
   },
   {
    "label": "표시",
    "value": "예시 (A 화면 실제 결과 아님)"
   }
  ],
  "staff": [
   {
    "staff": "intake",
    "name": "접수 직원",
    "bubble_key": "intake.fixture",
    "line1": "시연 자료 받음",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 접수 직원"
   },
   {
    "staff": "ledger",
    "name": "블록체인 기록관",
    "bubble_key": "ledger.not_found",
    "line1": "장부에 이 기관/문서 기록이 없어요",
    "line2": "PROOF_NOT_FOUND",
    "shape": "경고",
    "tone": "fail",
    "출처": "웹_설계.md 4.1 블록체인 기록관"
   },
   {
    "staff": "signature",
    "name": "서명 감정사",
    "bubble_key": "signature.no_source",
    "line1": "확인할 원본 없음",
    "line2": "",
    "shape": "해당 없음",
    "tone": "none",
    "출처": "웹_설계.md 4.1 서명 감정사"
   },
   {
    "staff": "original",
    "name": "원본 대조관",
    "bubble_key": "original.no_source",
    "line1": "확인할 원본 없음",
    "line2": "",
    "shape": "해당 없음",
    "tone": "none",
    "출처": "웹_설계.md 4.1 원본 대조관"
   },
   {
    "staff": "status",
    "name": "상태 확인관",
    "bubble_key": "status.no_source",
    "line1": "확인할 원본 없음",
    "line2": "",
    "shape": "해당 없음",
    "tone": "none",
    "출처": "웹_설계.md 4.1 상태 확인관"
   },
   {
    "staff": "ai",
    "name": "AI 분석가",
    "bubble_key": "ai.high",
    "line1": "위험 신호: 인증번호를 입력하세요",
    "line2": "HIGH · phishing-rules-0.1",
    "shape": "경고",
    "tone": "fail",
    "출처": "웹_설계.md 4.1 AI 분석가({quote}=인증번호를 입력하세요)"
   },
   {
    "staff": "report",
    "name": "보고서 담당",
    "bubble_key": "report.ready",
    "line1": "네 축 보고서를 정리했어요",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 보고서 담당"
   }
  ]
 },
 {
  "id": "revoked",
  "sample": true,
  "label": "예시",
  "button_label": "철회된 안내",
  "assumption": "A 화면 실제 결과에 없는 경우입니다(v1·v2에는 철회 값이 없음). 4.1 표 값(status.revoked)을 조합한 예시이며, v3에서는 VERIFIED와 철회가 함께 나올 수 있어 1.8 합성 규칙대로 '철회됨' 배지를 결론 앞에 둡니다.",
  "history": {
   "date": "2026-10-16",
   "title": "9월 보험료 납부 안내 (옛 QR)",
   "tone": "fail",
   "icon": "warn",
   "label": "철회됨"
  },
  "input": {
   "kind": "message",
   "text": "[OO공단] 9월 보험료 납부 안내입니다. 금액 42,300원. 아래 링크 또는 QR로 확인 후 납부하세요. https://verify.example/p/prf_9f8e7d6c5b4a39281706f5e4d3c2b1a0",
   "출처": "미확인",
   "메모": "피터가 만든 예시 문자."
  },
  "verification_status": "VERIFIED",
  "conclusion": {
   "badge": {
    "tone": "fail",
    "icon": "warn",
    "text": "철회됨"
   },
   "text": "기관이 이미 철회한 옛 안내예요. 발행 기록과 원본은 맞아요.",
   "출처": "미확인",
   "메모": "결론 문장: 배너 T1-b 제안(2026-10-19)"
  },
  "axes": [
   {
    "axis": "official",
    "name": "공식 발행",
    "status": "확인됨",
    "tone": "ok",
    "icon": "check",
    "body": "등록된 기관이 이 안내문을 발행한 기록이 있고, 서명도 그 기관 것이에요.",
    "staff": [
     "ledger",
     "signature"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "original",
    "name": "원본 일치",
    "status": "일치",
    "tone": "ok",
    "icon": "check",
    "body": "받은 내용이 원본과 한 글자도 다르지 않아요. 금액 42,300원도 원본과 같아요.",
    "staff": [
     "original"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태(금액 문장은 덧붙임)"
   },
   {
    "axis": "status",
    "name": "현재 상태",
    "status": "철회됨",
    "tone": "fail",
    "icon": "warn",
    "body": "기관이 이 안내를 철회했어요.",
    "staff": [
     "status"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "ai",
    "name": "AI 위험",
    "status": "뚜렷한 신호 없음",
    "tone": "info",
    "icon": "info",
    "body": "뚜렷한 위험 신호는 못 찾았어요. 문제가 없다는 뜻은 아니에요.",
    "note": "AI는 설명만 하고 발행 여부를 판정하지 않아요. 철회 여부는 상태 확인관만 알 수 있어요.",
    "staff": [
     "ai"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태(note 둘째 문장은 덧붙임)"
   }
  ],
  "ai_report": {
   "risk_level": "NO_CLEAR_INDICATORS",
   "evidence": [
    {
     "quote": "확인 후 납부하세요",
     "source": "input.text",
     "start_offset": 49,
     "end_offset": 59,
     "role": "request"
    }
   ],
   "matched_technique_ids": null,
   "출처": "미확인",
   "메모": "T1 예시 근거 위치(피터 작성). 실제 분석기 출력 아님. 수법 ID 는 자리만(목록 연결 전)."
  },
  "next_action": {
   "text": "이 안내대로 납부하지 마세요. 기관 공식 앱이나 공식 전화번호로 지금 유효한 안내를 다시 확인하세요.",
   "출처": "미확인",
   "메모": "새 문구(피터 작성)."
  },
  "details": [
   {
    "label": "검증 엔진 결과",
    "value": "VERIFIED (document.state=REVOKED)"
   },
   {
    "label": "쉬운 설명",
    "value": "검증 엔진 기준으로 발행 기록·서명·원본이 맞아요. 지금도 유효한지는 '현재 상태' 칸을 보세요."
   },
   {
    "label": "Proof ID",
    "value": "prf_9f8e7d6c5b4a39281706f5e4d3c2b1a0 (예시 값)"
   },
   {
    "label": "document.state",
    "value": "REVOKED"
   },
   {
    "label": "AI",
    "value": "NO_CLEAR_INDICATORS"
   },
   {
    "label": "표시",
    "value": "예시 (A 화면 실제 결과 아님)"
   }
  ],
  "staff": [
   {
    "staff": "intake",
    "name": "접수 직원",
    "bubble_key": "intake.fixture",
    "line1": "시연 자료 받음",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 접수 직원"
   },
   {
    "staff": "ledger",
    "name": "블록체인 기록관",
    "bubble_key": "ledger.recorded",
    "line1": "발행 기록 있음",
    "line2": "블록 #6,790,115",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 블록체인 기록관(2줄 블록 번호는 예시 값)"
   },
   {
    "staff": "signature",
    "name": "서명 감정사",
    "bubble_key": "signature.match",
    "line1": "기관 서명과 일치",
    "line2": "서명자 0x7c21…a4d0",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 서명 감정사(2줄 값은 예시)"
   },
   {
    "staff": "original",
    "name": "원본 대조관",
    "bubble_key": "original.same",
    "line1": "원본 그대로",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 원본 대조관"
   },
   {
    "staff": "status",
    "name": "상태 확인관",
    "bubble_key": "status.revoked",
    "line1": "철회된 안내예요",
    "line2": "REVOKED",
    "shape": "경고",
    "tone": "fail",
    "출처": "웹_설계.md 4.1 상태 확인관"
   },
   {
    "staff": "ai",
    "name": "AI 분석가",
    "bubble_key": "ai.no_clear",
    "line1": "뚜렷한 위험 신호는 못 찾았어요",
    "line2": "NO_CLEAR_INDICATORS",
    "shape": "정보",
    "tone": "info",
    "출처": "웹_설계.md 4.1 AI 분석가"
   },
   {
    "staff": "report",
    "name": "보고서 담당",
    "bubble_key": "report.ready",
    "line1": "네 축 보고서를 정리했어요",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 보고서 담당"
   }
  ]
 },
 {
  "id": "new_account",
  "sample": true,
  "label": "예시",
  "button_label": "새 계좌 요구",
  "assumption": "A 화면 실제 결과에 없는 경우입니다. 4.1 표 값(status.active, ai.caution — phishing-rules-0.1의 유일한 CAUTION 규칙 '새 계좌로 송금')을 조합한 예시입니다.",
  "history": {
   "date": "2026-10-15",
   "title": "결제 계좌 변경 안내",
   "tone": "caution",
   "icon": "caution",
   "label": "주의"
  },
  "input": {
   "kind": "message",
   "text": "[OO카드] 결제 계좌 변경 안내: 이번 달부터 기존 계좌 대신 새 계좌로 입금해 주세요. 새 계좌 OO은행 987-654-321098. 검증 링크: https://verify.example/p/prf_4d5e6f708192a3b4c5d6e7f8091a2b3c",
   "출처": "미확인",
   "메모": "피터가 만든 예시 문자."
  },
  "verification_status": "VERIFIED",
  "conclusion": {
   "badge": {
    "tone": "caution",
    "icon": "caution",
    "text": "주의"
   },
   "text": "새 계좌로 돈을 보내라는 문장이 있어요. 발행 기록과 원본은 맞아요.",
   "출처": "미확인",
   "메모": "결론 문장: 배너 T1-b 제안(2026-10-19)"
  },
  "axes": [
   {
    "axis": "official",
    "name": "공식 발행",
    "status": "확인됨",
    "tone": "ok",
    "icon": "check",
    "body": "등록된 기관이 이 안내문을 발행한 기록이 있고, 서명도 그 기관 것이에요.",
    "staff": [
     "ledger",
     "signature"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "original",
    "name": "원본 일치",
    "status": "일치",
    "tone": "ok",
    "icon": "check",
    "body": "받은 내용이 원본과 한 글자도 다르지 않아요.",
    "staff": [
     "original"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "status",
    "name": "현재 상태",
    "status": "유효",
    "tone": "ok",
    "icon": "check",
    "body": "지금도 유효한 안내예요.",
    "staff": [
     "status"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "ai",
    "name": "AI 위험",
    "status": "주의",
    "tone": "caution",
    "icon": "caution",
    "body": "주의: \"새 계좌로 입금해 주세요\"",
    "note": "AI는 설명만 하고 발행 여부를 판정하지 않아요. 규칙: 새 계좌로 송금을 요구하는 문장",
    "staff": [
     "ai"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태, 4.1 phishing-rules-0.1"
   }
  ],
  "ai_report": {
   "risk_level": "CAUTION",
   "evidence": [
    {
     "quote": "새 계좌로 입금해 주세요",
     "source": "input.text",
     "start_offset": 36,
     "end_offset": 49,
     "role": "risk"
    }
   ],
   "matched_technique_ids": null,
   "출처": "미확인",
   "메모": "T1 예시 근거 위치(피터 작성). 인용 문장은 기존 AI 칸 값과 같음. 수법 ID 는 자리만(목록 연결 전)."
  },
  "next_action": {
   "text": "새 계좌로 돈을 보내기 전에, 기관의 공식 전화번호로 계좌가 정말 바뀌었는지 직접 확인하세요.",
   "출처": "미확인",
   "메모": "새 문구(피터 작성). 1.8 보장하지 않는 것 1번과 같은 뜻."
  },
  "details": [
   {
    "label": "검증 엔진 결과",
    "value": "VERIFIED"
   },
   {
    "label": "쉬운 설명",
    "value": "검증 엔진 기준으로 발행 기록·서명·원본이 맞아요. 지금도 유효한지는 '현재 상태' 칸을 보세요."
   },
   {
    "label": "Proof ID",
    "value": "prf_4d5e6f708192a3b4c5d6e7f8091a2b3c (예시 값)"
   },
   {
    "label": "document.state",
    "value": "ACTIVE · warnings: []"
   },
   {
    "label": "AI",
    "value": "CAUTION · phishing-rules-0.1 · evidence: \"새 계좌로 입금해 주세요\""
   },
   {
    "label": "표시",
    "value": "예시 (A 화면 실제 결과 아님)"
   }
  ],
  "staff": [
   {
    "staff": "intake",
    "name": "접수 직원",
    "bubble_key": "intake.fixture",
    "line1": "시연 자료 받음",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 접수 직원"
   },
   {
    "staff": "ledger",
    "name": "블록체인 기록관",
    "bubble_key": "ledger.recorded",
    "line1": "발행 기록 있음",
    "line2": "블록 #6,805,462",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 블록체인 기록관(2줄 블록 번호는 예시 값)"
   },
   {
    "staff": "signature",
    "name": "서명 감정사",
    "bubble_key": "signature.match",
    "line1": "기관 서명과 일치",
    "line2": "서명자 0x3f9a…9e21",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 서명 감정사"
   },
   {
    "staff": "original",
    "name": "원본 대조관",
    "bubble_key": "original.same",
    "line1": "원본 그대로",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 원본 대조관"
   },
   {
    "staff": "status",
    "name": "상태 확인관",
    "bubble_key": "status.active",
    "line1": "현재 유효",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 상태 확인관"
   },
   {
    "staff": "ai",
    "name": "AI 분석가",
    "bubble_key": "ai.caution",
    "line1": "주의: 새 계좌로 입금해 주세요",
    "line2": "CAUTION · phishing-rules-0.1",
    "shape": "주의",
    "tone": "caution",
    "출처": "웹_설계.md 4.1 AI 분석가({quote}=새 계좌로 입금해 주세요)"
   },
   {
    "staff": "report",
    "name": "보고서 담당",
    "bubble_key": "report.ready",
    "line1": "네 축 보고서를 정리했어요",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 보고서 담당"
   }
  ]
 },
 {
  "id": "superseded",
  "sample": true,
  "label": "예시",
  "button_label": "고친 안내(v2)",
  "assumption": "A 화면 실제 결과에 없는 경우입니다(v1·v2에는 새 버전 값이 없음). 기관이 v1을 발행한 뒤 고친 v2를 발행해 v1이 SUPERSEDED가 된 장면을 4.1 표 값(status.superseded)으로 조합한 예시입니다. v3에서는 VERIFIED와 새 버전이 함께 나올 수 있어 1.8 합성 규칙대로 '새 버전 있음' 배지를 결론 앞에 둡니다.",
  "history": {
   "date": "2026-10-21",
   "title": "10월 건강보험료 납부 안내 (옛 버전)",
   "tone": "caution",
   "icon": "caution",
   "label": "새 버전 있음"
  },
  "input": {
   "kind": "message",
   "text": "[OO공단] 10월 건강보험료 납부 안내입니다. 금액 51,200원, 납부 기한 10월 31일. 안내 내용을 확인한 뒤 기한 안에 납부해 주세요. 확인: https://verify.example/p/prf_3c4d5e6f708192a3b4c5d6e7f8091a2b",
   "출처": "미확인",
   "메모": "피터가 만든 예시 문자(멘토 3회차 명령 1 프리셋 ①: 기관 발행 v1 → 수정 v2 대체)."
  },
  "verification_status": "VERIFIED",
  "conclusion": {
   "badge": {
    "tone": "caution",
    "icon": "caution",
    "text": "새 버전 있음"
   },
   "text": "기관이 고친 새 버전 v2가 있어요. 받은 안내는 옛 버전 v1이에요.",
   "출처": "미확인",
   "메모": "새 문구(피터 작성). 1.8 칸별 상태 '새 버전 있음'과 같은 뜻."
  },
  "axes": [
   {
    "axis": "official",
    "name": "공식 발행",
    "status": "확인됨",
    "tone": "ok",
    "icon": "check",
    "body": "등록된 기관이 이 안내문을 발행한 기록이 있고, 서명도 그 기관 것이에요.",
    "staff": [
     "ledger",
     "signature"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "original",
    "name": "원본 일치",
    "status": "일치",
    "tone": "ok",
    "icon": "check",
    "body": "받은 내용이 원본과 한 글자도 다르지 않아요. 금액 51,200원도 v1 원본과 같아요.",
    "staff": [
     "original"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태(금액 문장은 덧붙임)"
   },
   {
    "axis": "status",
    "name": "현재 상태",
    "status": "새 버전 있음",
    "tone": "caution",
    "icon": "caution",
    "body": "새 버전 v2가 있어요. 새 버전을 확인하세요.",
    "staff": [
     "status"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "ai",
    "name": "AI 위험",
    "status": "뚜렷한 신호 없음",
    "tone": "info",
    "icon": "info",
    "body": "뚜렷한 위험 신호는 못 찾았어요. 문제가 없다는 뜻은 아니에요.",
    "note": "AI는 설명만 하고 발행 여부를 판정하지 않아요. 새 버전이 있는지는 상태 확인관만 알 수 있어요.",
    "staff": [
     "ai"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태(note 둘째 문장은 덧붙임)"
   }
  ],
  "ai_report": {
   "risk_level": "NO_CLEAR_INDICATORS",
   "evidence": [
    {
     "quote": "기한 안에 납부해 주세요",
     "source": "input.text",
     "start_offset": 67,
     "end_offset": 80,
     "role": "request"
    }
   ],
   "matched_technique_ids": null,
   "출처": "미확인",
   "메모": "T1 예시 근거 위치(피터 작성). 실제 분석기 출력 아님. 수법 ID 는 자리만(목록 연결 전)."
  },
  "next_action": {
   "text": "이 옛 안내(v1)대로 납부하지 마세요. 기관 공식 앱이나 공식 전화번호로 새 버전 v2의 금액과 기한을 확인하세요.",
   "출처": "미확인",
   "메모": "새 문구(피터 작성)."
  },
  "details": [
   {
    "label": "검증 엔진 결과",
    "value": "VERIFIED (document.state=SUPERSEDED)"
   },
   {
    "label": "쉬운 설명",
    "value": "검증 엔진 기준으로 발행 기록·서명·원본이 맞아요. 지금도 유효한지는 '현재 상태' 칸을 보세요."
   },
   {
    "label": "Proof ID",
    "value": "prf_3c4d5e6f708192a3b4c5d6e7f8091a2b (예시 값)"
   },
   {
    "label": "document.state",
    "value": "SUPERSEDED · version=1 · latest_version=2"
   },
   {
    "label": "버전 기록",
    "value": "v1 발행 → v2 발행(v1 대체) · v1=SUPERSEDED, v2=ACTIVE (예시 값)"
   },
   {
    "label": "AI",
    "value": "NO_CLEAR_INDICATORS"
   },
   {
    "label": "표시",
    "value": "예시 (A 화면 실제 결과 아님)"
   }
  ],
  "staff": [
   {
    "staff": "intake",
    "name": "접수 직원",
    "bubble_key": "intake.fixture",
    "line1": "시연 자료 받음",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 접수 직원"
   },
   {
    "staff": "ledger",
    "name": "블록체인 기록관",
    "bubble_key": "ledger.recorded",
    "line1": "발행 기록 있음",
    "line2": "블록 #6,820,517",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 블록체인 기록관(2줄 블록 번호는 예시 값)"
   },
   {
    "staff": "signature",
    "name": "서명 감정사",
    "bubble_key": "signature.match",
    "line1": "기관 서명과 일치",
    "line2": "서명자 0x7c21…a4d0",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 서명 감정사(2줄 값은 예시)"
   },
   {
    "staff": "original",
    "name": "원본 대조관",
    "bubble_key": "original.same",
    "line1": "원본 그대로",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 원본 대조관"
   },
   {
    "staff": "status",
    "name": "상태 확인관",
    "bubble_key": "status.superseded",
    "line1": "새 버전 v2이 있어요",
    "line2": "state=SUPERSEDED · latestVersion=2",
    "shape": "주의",
    "tone": "caution",
    "출처": "웹_설계.md 4.1 상태 확인관({latest_version}=2)"
   },
   {
    "staff": "ai",
    "name": "AI 분석가",
    "bubble_key": "ai.no_clear",
    "line1": "뚜렷한 위험 신호는 못 찾았어요",
    "line2": "NO_CLEAR_INDICATORS",
    "shape": "정보",
    "tone": "info",
    "출처": "웹_설계.md 4.1 AI 분석가"
   },
   {
    "staff": "report",
    "name": "보고서 담당",
    "bubble_key": "report.ready",
    "line1": "네 축 보고서를 정리했어요",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 보고서 담당"
   }
  ]
 },
 {
  "id": "tamper_image",
  "sample": true,
  "label": "예시",
  "button_label": "고지서 이미지 금액 변조",
  "assumption": "A 화면 실제 결과에 없는 경우입니다. 안내문 이미지에서 AI가 글자를 읽어 낸 뒤(이미지 읽기는 이 시안에서 연결 전, 글자는 예시 값) 블록체인 원본 대조가 금액 변경(TAMPERED · AMOUNT_MISMATCH)을 찾는 장면을 4.1 표 값으로 조합한 예시입니다. '일반 챗봇' 말풍선은 비교용으로 지어낸 문구이며 실제 챗봇을 부르지 않았습니다.",
  "history": {
   "date": "2026-10-21",
   "title": "자동차세 고지서 이미지 금액 확인",
   "tone": "fail",
   "icon": "warn",
   "label": "원본과 다름"
  },
  "input": {
   "kind": "image",
   "image_label": "안내문 이미지에서 AI가 읽어 낸 글자 (예시)",
   "text": "[OO시청] 2026년 2기분 자동차세 고지서. 납부 금액 182,500원. 납부 기한 2026-10-31. 기한 내 아래 가상계좌로 납부해 주세요. 가상계좌 OO은행 562-01-998877. 확인: https://verify.example/p/prf_7a8b9c0d1e2f30415263748596a7b8c9",
   "출처": "미확인",
   "메모": "피터가 만든 예시 고지서 글자(멘토 3회차 명령 1 프리셋 ②: 금액만 바꾼 고지서 이미지). 원본 금액 128,500원 → 받은 이미지 182,500원."
  },
  "verification_status": "TAMPERED",
  "conclusion": {
   "badge": {
    "tone": "fail",
    "icon": "warn",
    "text": "원본과 다름"
   },
   "text": "원본과 금액이 달라요. 원본 128,500원, 받은 고지서 182,500원이에요.",
   "출처": "미확인",
   "메모": "결론 문장: 금액 변조 예시(배너 T1-b 제안 문장 꼴)를 고지서 값으로 바꿈."
  },
  "chatbot_compare": {
   "title": "일반 챗봇은 정상 공문으로 판단",
   "text": "자동차세 고지서 형식과 문구가 정상 공문과 같아 보여요. 기한 안에 가상계좌로 납부하시면 돼요.",
   "note": "비교용으로 지어낸 응답이에요. 실제 챗봇을 부르지 않았어요. 글자와 서식만 보면 금액이 바뀐 것을 알 수 없어요.",
   "출처": "미확인",
   "메모": "멘토 3회차 명령 4 비교 말풍선. 지어낸 문구(실제 챗봇 출력 아님)."
  },
  "axes": [
   {
    "axis": "official",
    "name": "공식 발행",
    "status": "확인됨",
    "tone": "ok",
    "icon": "check",
    "body": "등록된 기관이 이 안내문을 발행한 기록이 있고, 서명도 그 기관 것이에요.",
    "staff": [
     "ledger",
     "signature"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "original",
    "name": "원본 일치",
    "status": "불일치",
    "tone": "fail",
    "icon": "warn",
    "body": "바뀐 곳: 금액. 원본 128,500원 → 받은 고지서 182,500원 (54,000원 차이)",
    "staff": [
     "original"
    ],
    "compare": [
     {
      "label": "원본 금액",
      "value": "128,500원"
     },
     {
      "label": "받은 고지서 금액",
      "value": "182,500원",
      "changed": true
     }
    ],
    "출처": "웹_설계.md 1.8 칸별 상태(원 단위 금액은 덧붙임)"
   },
   {
    "axis": "status",
    "name": "현재 상태",
    "status": "확인 안 함",
    "tone": "none",
    "icon": "dash",
    "body": "앞 단계에서 멈춰 이 항목은 확인하지 않았어요.",
    "staff": [
     "status"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "ai",
    "name": "AI 위험",
    "status": "뚜렷한 신호 없음",
    "tone": "info",
    "icon": "info",
    "body": "뚜렷한 위험 신호는 못 찾았어요. 문제가 없다는 뜻은 아니에요.",
    "note": "AI는 설명만 하고 발행 여부를 판정하지 않아요. 이미지 글자는 AI가 읽었지만, 금액이 바뀐 것은 원본 대조관만 찾을 수 있어요.",
    "staff": [
     "ai"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태(note 둘째 문장은 덧붙임)"
   }
  ],
  "ai_report": {
   "risk_level": "NO_CLEAR_INDICATORS",
   "evidence": [
    {
     "quote": "기한 내 아래 가상계좌로 납부해 주세요",
     "source": "input.text",
     "start_offset": 61,
     "end_offset": 82,
     "role": "request"
    }
   ],
   "matched_technique_ids": null,
   "출처": "미확인",
   "메모": "T1 예시 근거 위치(피터 작성). 실제 분석기 출력 아님. 수법 ID 는 자리만(목록 연결 전)."
  },
  "next_action": {
   "text": "이 고지서의 금액으로 돈을 보내지 마세요. 기관 공식 앱이나 공식 전화번호로 원래 금액을 확인하세요.",
   "출처": "미확인",
   "메모": "금액 변조 예시의 다음 행동을 고지서에 맞게 고친 새 문구."
  },
  "details": [
   {
    "label": "검증 엔진 결과",
    "value": "TAMPERED · FULL_COMPARISON · AMOUNT_MISMATCH"
   },
   {
    "label": "쉬운 설명",
    "value": "원본과 다른 곳이 있어요."
   },
   {
    "label": "입력 종류",
    "value": "안내문 이미지 → AI 글자 읽기(예시 값, 이미지 읽기는 연결 전)"
   },
   {
    "label": "Proof ID",
    "value": "prf_7a8b9c0d1e2f30415263748596a7b8c9 (예시 값)"
   },
   {
    "label": "reason_codes",
    "value": "AMOUNT_MISMATCH"
   },
   {
    "label": "amount_minor",
    "value": "128500 → 182500 (KRW, 예시 값)"
   },
   {
    "label": "AI",
    "value": "NO_CLEAR_INDICATORS"
   },
   {
    "label": "표시",
    "value": "예시 (A 화면 실제 결과 아님)"
   }
  ],
  "staff": [
   {
    "staff": "intake",
    "name": "접수 직원",
    "bubble_key": "intake.fixture",
    "line1": "시연 자료 받음",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 접수 직원"
   },
   {
    "staff": "ledger",
    "name": "블록체인 기록관",
    "bubble_key": "ledger.recorded",
    "line1": "발행 기록 있음",
    "line2": "블록 #6,818,240",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 블록체인 기록관(2줄 블록 번호는 예시 값)"
   },
   {
    "staff": "signature",
    "name": "서명 감정사",
    "bubble_key": "signature.match",
    "line1": "기관 서명과 일치",
    "line2": "서명자 0x5b0e…c713",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 서명 감정사(2줄 값은 예시)"
   },
   {
    "staff": "original",
    "name": "원본 대조관",
    "bubble_key": "original.changed",
    "line1": "바뀐 곳: 금액",
    "line2": "AMOUNT_MISMATCH",
    "shape": "경고",
    "tone": "fail",
    "출처": "웹_설계.md 4.1 원본 대조관"
   },
   {
    "staff": "status",
    "name": "상태 확인관",
    "bubble_key": "status.not_run",
    "line1": "앞 단계에서 멈춰 확인 안 함",
    "line2": "",
    "shape": "해당 없음",
    "tone": "none",
    "출처": "웹_설계.md 4.1 상태 확인관"
   },
   {
    "staff": "ai",
    "name": "AI 분석가",
    "bubble_key": "ai.no_clear",
    "line1": "뚜렷한 위험 신호는 못 찾았어요",
    "line2": "NO_CLEAR_INDICATORS",
    "shape": "정보",
    "tone": "info",
    "출처": "웹_설계.md 4.1 AI 분석가"
   },
   {
    "staff": "report",
    "name": "보고서 담당",
    "bubble_key": "report.ready",
    "line1": "네 축 보고서를 정리했어요",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 보고서 담당"
   }
  ]
 },
 {
  "id": "unregistered",
  "sample": true,
  "label": "예시",
  "button_label": "미등록 기관 사칭",
  "assumption": "A 화면 실제 결과에 없는 경우입니다. 장부에 없는 기관 이름으로 보낸 문자를 4.1 표 값(ledger.not_found, *.no_source, ai.high)으로 조합한 예시입니다. 멘토 명령의 'UNVERIFIED'는 코드 값이 아니어서 검증 엔진 값 NOT_REGISTERED(ISSUER_NOT_FOUND)로 옮겼습니다. 시연 표기 UNVERIFIED는 js/api_adapter.js 의 DEMO_TERM 대응표로 이어 '자세히'의 '시연 표기' 행에 보여 줍니다.",
  "history": {
   "date": "2026-10-21",
   "title": "미환급금 신청 안내 문자",
   "tone": "fail",
   "icon": "warn",
   "label": "기록 없음"
  },
  "input": {
   "kind": "message",
   "text": "[OO환급센터] 고객님 미환급금 384,000원이 확인되었습니다. 오늘 안에 신청하지 않으면 소멸됩니다. 상담원 안내에 따라 원격 지원 앱을 설치해 주세요. https://refund-center.example/p/prf_e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
   "출처": "미확인",
   "메모": "피터가 만든 예시 문자(멘토 3회차 명령 1 프리셋 ③: 미등록 사칭 문자). 기관 이름은 OO로 가림."
  },
  "verification_status": "NOT_REGISTERED",
  "conclusion": {
   "badge": {
    "tone": "fail",
    "icon": "warn",
    "text": "기록 없음"
   },
   "text": "장부에 이 기관의 발행 기록이 없고, 원격 지원 앱 설치를 요구하는 문장이 있어요.",
   "출처": "미확인",
   "메모": "새 문구(피터 작성). 사칭 문자 예시의 결론 문장 꼴."
  },
  "axes": [
   {
    "axis": "official",
    "name": "공식 발행",
    "status": "기록 없음",
    "tone": "fail",
    "icon": "warn",
    "body": "장부에서 이 기관 또는 이 문서의 발행 기록을 찾지 못했어요.",
    "staff": [
     "ledger",
     "signature"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "original",
    "name": "원본 일치",
    "status": "확인할 원본 없음",
    "tone": "none",
    "icon": "dash",
    "body": "비교할 원본이 없어서 확인하지 않았어요.",
    "staff": [
     "original"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태"
   },
   {
    "axis": "status",
    "name": "현재 상태",
    "status": "확인할 원본 없음",
    "tone": "none",
    "icon": "dash",
    "body": "비교할 원본이 없어서 지금 상태를 확인하지 않았어요.",
    "staff": [
     "status"
    ],
    "출처": "미확인",
    "메모": "1.8 표에 현재 상태 칸의 '원본 없음' 행이 없어 원본 일치 칸 문구를 고쳐 씀(사칭 문자 예시와 같음)."
   },
   {
    "axis": "ai",
    "name": "AI 위험",
    "status": "위험 신호",
    "tone": "fail",
    "icon": "warn",
    "body": "위험 신호: \"원격 지원 앱을 설치해 주세요\"",
    "note": "AI는 설명만 하고 발행 여부를 판정하지 않아요. 규칙: 원격 제어 앱 설치를 요구하는 문장, 급하게 재촉하는 문장",
    "staff": [
     "ai"
    ],
    "출처": "웹_설계.md 1.8 칸별 상태, 4.1 phishing-rules-0.1"
   }
  ],
  "ai_report": {
   "risk_level": "HIGH",
   "evidence": [
    {
     "quote": "오늘 안에 신청하지 않으면 소멸됩니다",
     "source": "input.text",
     "start_offset": 37,
     "end_offset": 57,
     "role": "risk"
    },
    {
     "quote": "원격 지원 앱을 설치해 주세요",
     "source": "input.text",
     "start_offset": 70,
     "end_offset": 86,
     "role": "risk"
    }
   ],
   "matched_technique_ids": null,
   "출처": "미확인",
   "메모": "T1 예시 근거 위치(피터 작성). 규칙 이름은 4.1 phishing-rules-0.1 의 '원격 제어 설치'·'급한 송금'을 참고했지만 실제 분석기 출력 아님. 수법 ID 는 자리만(목록 연결 전)."
  },
  "next_action": {
   "text": "앱을 설치하거나 링크를 누르지 마세요. 환급 안내는 기관의 공식 전화번호로 직접 확인하세요.",
   "출처": "미확인",
   "메모": "새 문구(피터 작성)."
  },
  "details": [
   {
    "label": "검증 엔진 결과",
    "value": "NOT_REGISTERED"
   },
   {
    "label": "쉬운 설명",
    "value": "장부에서 등록된 발행 기록을 찾지 못했어요."
   },
   {
    "label": "Proof ID",
    "value": "prf_e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0 (예시 값, 장부에 없음)"
   },
   {
    "label": "reason_codes",
    "value": "ISSUER_NOT_FOUND"
   },
   {
    "label": "checks",
    "value": "issuer=NOT_FOUND"
   },
   {
    "label": "AI",
    "value": "HIGH · phishing-rules-0.1 · evidence 2개"
   },
   {
    "label": "표시",
    "value": "예시 (A 화면 실제 결과 아님)"
   }
  ],
  "staff": [
   {
    "staff": "intake",
    "name": "접수 직원",
    "bubble_key": "intake.fixture",
    "line1": "시연 자료 받음",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 접수 직원"
   },
   {
    "staff": "ledger",
    "name": "블록체인 기록관",
    "bubble_key": "ledger.not_found",
    "line1": "장부에 이 기관/문서 기록이 없어요",
    "line2": "ISSUER_NOT_FOUND",
    "shape": "경고",
    "tone": "fail",
    "출처": "웹_설계.md 4.1 블록체인 기록관"
   },
   {
    "staff": "signature",
    "name": "서명 감정사",
    "bubble_key": "signature.no_source",
    "line1": "확인할 원본 없음",
    "line2": "",
    "shape": "해당 없음",
    "tone": "none",
    "출처": "웹_설계.md 4.1 서명 감정사"
   },
   {
    "staff": "original",
    "name": "원본 대조관",
    "bubble_key": "original.no_source",
    "line1": "확인할 원본 없음",
    "line2": "",
    "shape": "해당 없음",
    "tone": "none",
    "출처": "웹_설계.md 4.1 원본 대조관"
   },
   {
    "staff": "status",
    "name": "상태 확인관",
    "bubble_key": "status.no_source",
    "line1": "확인할 원본 없음",
    "line2": "",
    "shape": "해당 없음",
    "tone": "none",
    "출처": "웹_설계.md 4.1 상태 확인관"
   },
   {
    "staff": "ai",
    "name": "AI 분석가",
    "bubble_key": "ai.high",
    "line1": "위험 신호: 원격 지원 앱을 설치해 주세요",
    "line2": "HIGH · phishing-rules-0.1",
    "shape": "경고",
    "tone": "fail",
    "출처": "웹_설계.md 4.1 AI 분석가({quote}=원격 지원 앱을 설치해 주세요)"
   },
   {
    "staff": "report",
    "name": "보고서 담당",
    "bubble_key": "report.ready",
    "line1": "네 축 보고서를 정리했어요",
    "line2": "",
    "shape": "확인됨",
    "tone": "ok",
    "출처": "웹_설계.md 4.1 보고서 담당"
   }
  ]
 }
];
