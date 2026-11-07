// 개인 회원 아이디: 가입 화면이 아이디를 서버로 보내고, 로그인은 아이디 또는 이메일로 한다
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const WEB = path.join(__dirname, '..', '페이지');

test('가입: 아이디 규칙(영문·한글·숫자·_ 3~40자)이 서버 규칙과 같고 아이디 오류 문구가 있음', () => {
  const join = fs.readFileSync(path.join(WEB, 'join.html'), 'utf8');
  assert.match(join, /\/\^\[A-Za-z0-9_가-힣\]\{3,40\}\$\/\.test\(user\)/);
  assert.match(join, /INVALID_USERNAME:"아이디는/);
  const re = /^[A-Za-z0-9_가-힣]{3,40}$/;
  for (const ok of ['노랑이', 'star5937', 'a_b']) assert.ok(re.test(ok), ok);
  for (const bad of ['ab', 'a@b.invalid', 'has space', 'dash-no']) assert.ok(!re.test(bad), bad);
});

test('로그인: 칸 이름이 아이디 또는 이메일', () => {
  const login = fs.readFileSync(path.join(WEB, 'login.html'), 'utf8');
  assert.match(login, /<label for="username">아이디 또는 이메일<\/label>/);
});
