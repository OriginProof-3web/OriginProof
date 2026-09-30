# Web UI

- A: apps/web, 본선 사용자·발행자·운영자 화면과 UX·접근성. 로컬 웹은 P0입니다.
- 실제 선행 API가 없더라도 합의된 계약과 mock으로 독립 구현·검사할 수 있습니다. 실제 연결 완료는 별도 검증합니다.
- 생성 TypeScript 타입과 API 경계를 사용하고 검증 규칙을 복제하거나 OpenAI를 직접 호출하지 않습니다.
- verification status·lifecycle·현재 사용 가능성을 구분합니다. ID 조회만으로 내용 일치를 표시하지 않습니다.
- loading·empty·partial·error·권한 거부와 모바일/데스크톱 접근성을 검사합니다.
