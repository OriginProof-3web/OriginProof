'use strict';
// 사진 입력. 화면 시험은 DOM 대역(브라우저 미검증)
const test = require('node:test'); const assert = require('node:assert/strict');
const path = require('node:path'); const { Readable } = require('node:stream'); const { pathToFileURL } = require('node:url');
const { ROOT, page, sleep } = require('./_review_common.js');
const ME = { status: 200, body: { username: 'u', csrf_token: 'tok' } };   // op5_auth 는 username 으로 회원 판단
const HIGH = { analysis_id: 'ana_img', status: 'COMPLETED', retain_report: false, retain_original: false, report: { risk_level: 'HIGH', evidence: [{ rule_id: 'R_OTP', quote: '인증번호를 입력하세요', start_offset: 3, end_offset: 14, source: 'RULE' }], limitations: [] } };
class FR { readAsDataURL(f) { this.result = 'data:' + f.type + ';base64,QUJD'; this.onload(); } }
function route(u, i) {
  if (u === '/api/v1/auth/me') return ME;
  if (u === '/api/v3/inputs') return { status: 201, body: { input_ref: 'inp_x', expires_at: 1 } };
  if (u === '/api/v3/analyses' && i.method === 'POST') return { status: 202, body: HIGH };
  return null;
}
async function photo(d, name) {
  d.win.dispatchEvent(new d.win.CustomEvent('op5:image', { detail: { file: { name, type: 'image/png', size: 10 }, id: 'att_' + name } }));   // R1-B T9 뒤 business.html 이 보내는 모양(id 필수)
  await sleep(10);
  const btn = d.doc.querySelectorAll('button').filter(b => b.textContent === '이 사진 확인하기').pop();
  assert.ok(btn); btn.click();
}
test('사진 분석의 근거를 파일 이름 글에 대보지 않음: "받은 글"에 파일 이름 없음, 거짓 위치 사유 없음(브라우저 미검증)', async () => {
  const d = page(route, { FileReader: FR });
  await sleep(40);
  await photo(d, 'a.png');
  await sleep(150);
  const ai = d.doc.querySelectorAll('section.op-ai').pop().textContent;
  assert.equal(d.win.fetch.calls.filter(c => c.url === '/api/v3/inputs').length, 1);
  assert.match(ai, /인증번호를 입력하세요/);
  assert.doesNotMatch(ai, /받은 글에 없는 문장|위치의 글과 근거 문장이 다름|위치가 글 길이를 넘음/);
  assert.doesNotMatch(ai, /받은 글\[문서 사진\]/);
});
test('프록시: 5MB 사진 본문(≈6.7MB base64)을 /api/v3/inputs 로 전달, 다른 경로는 1MB 유지, 7MB+1KB 초과 거부', async () => {
  const { createHandler } = await import(pathToFileURL(path.join(ROOT, '개발/op5-proxy.mjs')).href);
  const calls = [];
  const h = createHandler({ port: 8790, forward: async (r) => { calls.push(r); return { status: 201, headers: { 'content-type': 'application/json' }, body: Buffer.from('{}') }; } });
  const send = async (url, n) => {
    const r = Readable.from([Buffer.alloc(n, 0x41)]);
    Object.assign(r, { method: 'POST', url, headers: { host: '127.0.0.1:8790', origin: 'http://127.0.0.1:8790', 'content-type': 'application/json' } });
    const res = { status: 0, writeHead(s) { this.status = s; }, end() { this.ended = true; } };
    await h(r, res); return res.status;
  };
  const big = Math.ceil(5 * 1024 * 1024 * 4 / 3) + 200;
  assert.equal(await send('/api/v3/inputs', big), 201);
  assert.equal(await send('/api/v3/inputs', 7 * 1024 * 1024 + 2048), 413);
  assert.equal(await send('/api/v3/document-lookups', 1024 * 1024 + 1), 413);
  assert.equal(calls.length, 1);
});
