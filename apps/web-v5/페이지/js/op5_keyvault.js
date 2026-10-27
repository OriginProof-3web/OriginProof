/* 5안 개인 회원의 AI API 키 보관함 — 이 기기에만, 암호화해서만 둔다.
   보안 규칙
   - 키를 OriginProof 서버나 다른 곳으로 보내지 않는다(이 파일에는 네트워크 호출이 없다). 페이지 CSP 도 connect-src 'self'.
   - 평문 키를 저장하지 않는다. 회원 비밀번호에서 PBKDF2-SHA256(600,000회)로 만든 AES-GCM-256 키로 암호화한 값만
     localStorage('op5.aikey')에 둔다. 소금(16바이트)·IV(12바이트)는 저장할 때마다 새로 만든다.
   - 화면·로그·오류 메시지에 키를 쓰지 않는다. 보여 줄 때는 끝 4자리만(마스킹).
   - "이 기기에 저장 안 함"을 고르면 아무것도 남기지 않는다.
   - 암호화한 값도 지울 수 있다(remove). 로그아웃할 때 지우도록 화면에서 묻는다.
   주의: 브라우저 저장은 이 기기를 쓰는 사람이 비밀번호를 알면 풀 수 있다. 서버 보관(C 계약)이 생기면 그쪽으로 옮긴다. */
(function (root) {
  'use strict';
  var KEY = 'op5.aikey', ITER = 600000;
  var PROVIDERS = {
    openai: { name: 'GPT (OpenAI)', re: /^sk-(proj-|svcacct-|admin-)?[A-Za-z0-9_-]{20,}$/, hint: 'sk- 로 시작' },
    anthropic: { name: 'Claude (Anthropic)', re: /^sk-ant-[A-Za-z0-9_-]{20,}$/, hint: 'sk-ant- 로 시작' }
  };
  var enc = new TextEncoder(), dec = new TextDecoder();
  function b64(u8) { var s = ''; for (var i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]); return btoa(s); }
  function unb64(s) { var b = atob(s), u = new Uint8Array(b.length); for (var i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u; }
  function store() { try { return root.localStorage; } catch (e) { return null; } }
  function ready() { return !!(root.crypto && root.crypto.subtle && root.isSecureContext !== false); }

  function check(provider, key) {
    var p = PROVIDERS[provider];
    if (!p) return '어떤 AI를 쓸지 골라 주세요.';
    if (typeof key !== 'string' || !key.trim()) return 'API 키를 넣어 주세요.';
    if (/\s/.test(key.trim()) === false && key !== key.trim()) key = key.trim();
    // Claude 키(sk-ant-)도 GPT 형식에 걸리므로 먼저 거른다
    if (provider === 'openai' && /^sk-ant-/.test(key.trim())) return 'Claude(Anthropic) 키 같아요. 위에서 Claude를 골라 주세요.';
    if (!p.re.test(key.trim())) {
      if (provider === 'anthropic' && /^sk-(?!ant-)/.test(key.trim())) return 'GPT(OpenAI) 키 같아요. 위에서 GPT를 골라 주세요.';
      return p.name + ' 키 형식이 아니에요(' + p.hint + ').';
    }
    return '';
  }
  function mask(key) { var k = String(key || '').trim(); return k.length > 8 ? k.slice(0, k.indexOf('-', 3) > 0 ? k.indexOf('-', 3) + 1 : 3) + '••••' + k.slice(-4) : '••••'; }

  function derive(password, salt) {
    return root.crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveKey']).then(function (base) {
      return root.crypto.subtle.deriveKey({ name: 'PBKDF2', salt: salt, iterations: ITER, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
    });
  }

  /* 암호화해서 저장. 성공하면 {provider, hint} 만 돌려준다(키는 돌려주지 않음) */
  function save(provider, key, password) {
    var err = check(provider, key);
    if (err) return Promise.reject(new Error(err));
    if (typeof password !== 'string' || password.length < 8) return Promise.reject(new Error('키를 잠글 비밀번호는 8자 이상이어야 해요.'));
    if (!ready()) return Promise.reject(new Error('이 브라우저에서는 안전한 암호화를 쓸 수 없어 저장하지 않았어요.'));
    var k = key.trim(), salt = root.crypto.getRandomValues(new Uint8Array(16)), iv = root.crypto.getRandomValues(new Uint8Array(12));
    var hint = k.slice(-4);
    return derive(password, salt).then(function (aes) {
      // provider 를 추가 인증 데이터로 묶어, 저장값의 AI 종류를 바꿔치기하면 풀리지 않게 한다
      return root.crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv, additionalData: enc.encode(provider) }, aes, enc.encode(k));
    }).then(function (ct) {
      var s = store(); if (!s) throw new Error('이 브라우저는 저장을 막아 두었어요. 저장하지 않았어요.');
      s.setItem(KEY, JSON.stringify({ v: 1, provider: provider, alg: 'PBKDF2-SHA256-600000/AES-GCM-256', salt: b64(salt), iv: b64(iv), ct: b64(new Uint8Array(ct)), hint: hint, savedAt: new Date().toISOString() }));
      k = null;
      return { provider: provider, name: PROVIDERS[provider].name, hint: '••••' + hint };
    });
  }

  /* 저장된 정보(평문 키 없이) */
  function info() {
    var s = store(); if (!s) return null;
    try { var o = JSON.parse(s.getItem(KEY) || 'null'); return o && o.v === 1 ? { provider: o.provider, name: (PROVIDERS[o.provider] || {}).name || o.provider, hint: '••••' + o.hint, savedAt: o.savedAt } : null; } catch (e) { return null; }
  }

  /* 비밀번호로 풀리는지만 확인(키 자체는 밖으로 내보내지 않음) */
  function verify(password) {
    var s = store(), o; try { o = JSON.parse((s && s.getItem(KEY)) || 'null'); } catch (e) { o = null; }
    if (!o) return Promise.resolve(false);
    return derive(password, unb64(o.salt)).then(function (aes) {
      return root.crypto.subtle.decrypt({ name: 'AES-GCM', iv: unb64(o.iv), additionalData: enc.encode(o.provider) }, aes, unb64(o.ct));
    }).then(function (pt) { var ok = dec.decode(pt).length > 0; pt = null; return ok; }, function () { return false; });
  }

  function remove() { var s = store(); if (s) s.removeItem(KEY); }

  root.OP5KeyVault = { PROVIDERS: PROVIDERS, check: check, mask: mask, save: save, info: info, verify: verify, remove: remove, ready: ready };
})(window);
