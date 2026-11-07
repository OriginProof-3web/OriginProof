// View validation mirrors C #35. The server remains the authority.
export function issueErrors(fields, recipient, expiry, now = Date.now()) {
 /** @type {Record<string,string>} */
 const errors = {};
 for (const [name, value] of Object.entries(fields)) {
  if (!value.trim()) errors[name] = '필수 항목을 입력해 주세요.';
  if (['amount_minor','version'].includes(name) && (!/^\d+$/.test(value) || !Number.isSafeInteger(Number(value)) || Number(value) <= 0)) errors[name] = '0보다 큰 정수를 입력해 주세요.';
 }
 if (fields.currency !== undefined && !/^[A-Z]{3}$/.test(fields.currency)) errors.currency = 'KRW처럼 영문 대문자 3자로 입력해 주세요.';
 if (!recipient) errors.recipient_id = '지정 수신자를 선택해 주세요.';
 if (!expiry || !Number.isFinite(Date.parse(expiry)) || Date.parse(expiry) <= now) errors.expires_at = '현재보다 늦은 만료 시각을 선택해 주세요.';
 return errors;
}
export function validationErrors(detail) {
 /** @type {Record<string,string>} */
 const errors = {};
 if (!Array.isArray(detail)) return errors;
 for (const item of detail) {
  const name = item.loc?.at(-1);
  if (typeof name === 'string') errors[name] = String(item.msg ?? '입력값을 확인해 주세요.');
 }
 return errors;
}
export function proofLink(id, base) {
 const url = new URL('index.html', base);
 url.searchParams.set('proof_id', id);
 url.hash = 'user';
 return url.href;
}
