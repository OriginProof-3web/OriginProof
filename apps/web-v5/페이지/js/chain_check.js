/* 체인에서 직접 확인 (대표 명령 2026-10-21).
   브라우저가 OriginProof 서버를 거치지 않고 블록체인 RPC 에 직접 물어, 서버 응답의 문서 값과 체인 값이 같은지 비교함.
   - 읽기 전용 JSON-RPC 세 가지만 씀: eth_chainId, eth_call, (서버 응답에 거래 해시가 있을 때만) eth_getTransactionReceipt.
     개인키·서명·거래 보내기 없음. 외부 라이브러리·CDN 없음(fetch 와 아래 작은 ABI 함수만).
   - Anvil(http://127.0.0.1:8545)과 Sepolia 는 같은 코드. 다른 것은 설정 값(RPC 주소·레지스트리 주소·체인 ID)뿐.
   - 화면(DOM)을 만지지 않음 → node 에서 가짜 fetch 로 시험(tools/chain_check.test.js).
   - 브라우저: window.Hk.chain / node: require('../web-prototype/js/chain_check.js')

   함수 서명 출처(읽기만 함): OriginProof-감사 origin/codex/v5-w5-b-live-recovery
     packages/contracts/src/IOriginProofWalletRegistry.sol
       latestVersion(bytes32) returns (uint64)
       getDocument(bytes32,uint64) returns (DocumentVersion)   // 정적 struct 12칸, state 1 ACTIVE · 2 REVOKED · 3 SUPERSEDED
       getIssuer(bytes32) returns (uint8 state, bytes32 keyId, address signer, bytes32 metadataHash)
     packages/contracts/src/OriginProofWalletRegistry.sol  error UnknownDocument()  (getDocument 에 기록이 없으면 되돌림)
     packages/contracts/src/OriginProofWalletGovernance.sol error UnknownIssuer()   (getIssuer 에 기관이 없으면 되돌림, state 1 활성 · 2 정지)
   selector = keccak256(서명) 앞 4바이트. 값은 tools/chain_abi_check.py(순수 파이썬 keccak256)로 계산·대조함. */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else { root.Hk = root.Hk || {}; root.Hk.chain = api; }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var SELECTORS = { latestVersion: '0xe9e10752', getDocument: '0x49b53539', getIssuer: '0x2341c963', UnknownDocument: '0x7e7b5a7a', UnknownIssuer: '0x3264d6ca' };
  var METHODS = ['eth_chainId', 'eth_call', 'eth_getTransactionReceipt'];   // 이 밖의 방법은 부르지 않음(rpc 에서 막음)
  var TIMEOUT_MS = 8000;
  var SEPOLIA = '11155111';
  var LOOPBACK = ['127.0.0.1', 'localhost', '[::1]'];

  // 결과 머리 문구(대표 명령 글자 그대로 4종 + 연결 전·체인 ID 다름·비교할 값 없음)
  var TEXT = {
    match: '체인 기록과 일치(독립 확인)',
    mismatch: '체인 기록과 다름',
    rpc_fail: '체인에 연결하지 못함 — 판단 보류',
    sample: '예시라 체인 확인 불가',
    not_configured: '연결 전',
    chain_hold: '체인 ID가 설정과 달라 판단 보류',
    no_claim: '서버 응답에 체인과 맞춰 볼 값이 없어 판단 보류'
  };
  var TONE = { match: 'ok', mismatch: 'fail', rpc_fail: 'pending', sample: 'none', not_configured: 'offline', chain_hold: 'pending', no_claim: 'pending' };
  var SHAPE = { ok: '확인됨', fail: '경고', pending: '보류', none: '해당 없음', offline: '연결 전' };
  var STATE_KO = { ACTIVE: '유효', REVOKED: '철회됨', SUPERSEDED: '새 버전 있음', EXPIRED: '만료' };
  var CHAIN_STATE = { 1: 'ACTIVE', 2: 'REVOKED', 3: 'SUPERSEDED' };

  var HEX32 = /^0x[0-9a-f]{64}$/;
  var ADDR = /^0x[0-9a-fA-F]{40}$/;

  /* ------------------------------ 설정 (RPC 주소·레지스트리 주소·체인 ID) ------------------------------
     기본값은 모두 빈칸 → '연결 전'(호출 안 함). 저장 키는 기존 설정과 따로(jjin.chain.v1). */
  var KEY = 'jjin.chain.v1';
  var EMPTY = { rpcUrl: '', registry: '', chainId: '' };

  function checkRpcUrl(v) {
    if (typeof v !== 'string') return { ok: false, message: '주소 형식이 맞지 않아요.' };
    var s = v.trim();
    if (!s) return { ok: true, value: '' };
    if (s.length > 300) return { ok: false, message: '주소가 너무 길어요(300자까지).' };
    var u;
    try { u = new URL(s); } catch (e) { return { ok: false, message: '주소 형식이 맞지 않아요. 예: http://127.0.0.1:8545' }; }
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return { ok: false, message: 'http 또는 https 주소만 받아요.' };
    if (u.username || u.password) return { ok: false, message: '계정 정보(아이디·비밀번호)가 든 주소는 받지 않아요.' };
    if (u.hash) return { ok: false, message: '# 뒤 글자가 붙은 주소는 받지 않아요.' };
    if (u.protocol === 'http:' && LOOPBACK.indexOf(u.hostname) < 0) return { ok: false, message: '바깥 주소는 https 로만 받아요. http 는 이 컴퓨터 주소(127.0.0.1·localhost)만 돼요.' };
    return { ok: true, value: u.href };
  }
  function checkRegistry(v) {
    if (typeof v !== 'string') return { ok: false, message: '레지스트리 주소 형식이 맞지 않아요.' };
    var s = v.trim();
    if (!s) return { ok: true, value: '' };
    if (!ADDR.test(s)) return { ok: false, message: '레지스트리 주소는 0x 다음 16진수 40자리예요.' };
    if (/^0x0{40}$/.test(s)) return { ok: false, message: '0 주소는 받지 않아요.' };
    return { ok: true, value: s.toLowerCase() };
  }
  function checkChainId(v) {
    var s = typeof v === 'number' ? String(v) : (typeof v === 'string' ? v.trim() : null);
    if (s == null) return { ok: false, message: '체인 ID 형식이 맞지 않아요.' };
    if (!s) return { ok: true, value: '' };
    if (!/^[1-9][0-9]{0,15}$/.test(s) || Number(s) > Number.MAX_SAFE_INTEGER) return { ok: false, message: '체인 ID는 1 이상의 정수예요. 예: Anvil 31337, Sepolia 11155111' };
    return { ok: true, value: s };
  }
  var CHECK = { rpcUrl: checkRpcUrl, registry: checkRegistry, chainId: checkChainId };

  function normalizeSettings(raw) {
    var src = raw && typeof raw === 'object' ? raw : {};
    var out = {};
    Object.keys(CHECK).forEach(function (k) { var r = CHECK[k](src[k] == null ? '' : src[k]); out[k] = r.ok ? r.value : ''; });
    return out;
  }

  // set(field, raw) → { ok, value, message }. 틀린 값은 저장하지 않고 이전 값을 그대로 씀
  function createStore(storage) {
    var cur = EMPTY;
    try { cur = normalizeSettings(JSON.parse(storage ? storage.getItem(KEY) : 'null')); } catch (e) { cur = normalizeSettings(null); }
    function save() { try { if (storage) storage.setItem(KEY, JSON.stringify(cur)); } catch (e) { /* 막혀 있으면 이 창에서만 */ } }
    return {
      get: function () { return { rpcUrl: cur.rpcUrl, registry: cur.registry, chainId: cur.chainId }; },
      set: function (field, raw) {
        if (!CHECK[field]) return { ok: false, value: '', message: '모르는 설정이에요.' };
        var r = CHECK[field](raw);
        if (!r.ok) return { ok: false, value: cur[field], message: r.message };
        var next = Object.assign({}, cur);
        next[field] = r.value;
        cur = normalizeSettings(next);
        save();
        return { ok: true, value: cur[field], message: '' };
      }
    };
  }

  /* ------------------------------ ABI 인코딩·디코딩 (정적 타입만: bytes32·uint·address) ------------------------------ */
  function strip(h) { return h.slice(0, 2) === '0x' ? h.slice(2) : h; }
  function encBytes32(h) {
    if (typeof h !== 'string' || !/^0x[0-9a-fA-F]{64}$/.test(h)) throw new Error('bytes32 형식 아님');
    return strip(h).toLowerCase();
  }
  function encUint(n, bits) {
    var b = typeof n === 'bigint' ? n : BigInt(n);
    if (b < 0n || b >= (1n << BigInt(bits))) throw new Error('uint' + bits + ' 범위 밖');
    return b.toString(16).padStart(64, '0');
  }
  function encodeCall(name, args) {
    if (name === 'latestVersion') return SELECTORS.latestVersion + encBytes32(args[0]);
    if (name === 'getDocument') return SELECTORS.getDocument + encBytes32(args[0]) + encUint(args[1], 64);
    if (name === 'getIssuer') return SELECTORS.getIssuer + encBytes32(args[0]);
    throw new Error('모르는 함수: ' + name);
  }

  // hex 결과를 32바이트 칸으로 나눔. 칸 수가 정확히 맞아야 함(정적 반환값이라 길이가 정해져 있음)
  function words(hex, n) {
    if (typeof hex !== 'string' || !/^0x([0-9a-fA-F]{64})*$/.test(hex)) throw new Error('응답 hex 형식 아님');
    var h = strip(hex).toLowerCase();
    if (h.length !== n * 64) throw new Error('응답 길이가 ' + n + '칸이 아님(' + h.length / 64 + '칸)');
    var out = [];
    for (var i = 0; i < n; i++) out.push(h.slice(i * 64, i * 64 + 64));
    return out;
  }
  // uint: 위쪽 남는 비트가 0이어야 함(정규 인코딩, 서버 wallet_rpc.py 의 다시-인코딩 비교와 같은 뜻)
  function decUint(w, bits) {
    var b = BigInt('0x' + w);
    if (b >= (1n << BigInt(bits))) throw new Error('uint' + bits + ' 범위 밖');
    return b <= BigInt(Number.MAX_SAFE_INTEGER) ? Number(b) : b.toString();
  }
  function decAddress(w) {
    if (!/^0{24}/.test(w)) throw new Error('address 위쪽 12바이트가 0이 아님');
    return '0x' + w.slice(24);
  }
  function decBytes32(w) { return '0x' + w; }

  var DOC_FIELDS = [
    ['issuerId', 'b'], ['docKey', 'b'], ['version', 64], ['keyId', 'b'], ['originalHash', 'b'], ['protectedHash', 'b'],
    ['contentSchema', 'b'], ['issuedAt', 64], ['expiresAt', 64], ['publishedAt', 64], ['publishedBlock', 64], ['state', 8]
  ];
  function decodeDocument(hex) {
    var w = words(hex, DOC_FIELDS.length);
    var o = {};
    DOC_FIELDS.forEach(function (f, i) { o[f[0]] = f[1] === 'b' ? decBytes32(w[i]) : decUint(w[i], f[1]); });
    return o;
  }
  function decodeLatestVersion(hex) { return decUint(words(hex, 1)[0], 64); }
  function decodeIssuer(hex) {
    var w = words(hex, 4);
    return { state: decUint(w[0], 8), keyId: decBytes32(w[1]), signer: decAddress(w[2]), metadataHash: decBytes32(w[3]) };
  }

  /* ------------------------------ 서버 응답에서 비교할 값 ------------------------------
     v3 VerificationResult(wallet_contract.py:369-396): chain_id·verifying_contract·checked_at·block_number + document(DocumentView:321-335).
     형식이 하나라도 틀리면 null(비교할 값 없음). 거래 해시는 VerificationResult 에 없어 보통 null. */
  function claimFrom(d) {
    if (!d || typeof d !== 'object') return null;
    var doc = d.document;
    if (!doc || typeof doc !== 'object') return null;
    var hexes = ['document_id', 'issuer_id', 'doc_key', 'key_id', 'original_hash', 'protected_hash', 'content_schema'];
    if (hexes.some(function (k) { return typeof doc[k] !== 'string' || !HEX32.test(doc[k]); })) return null;
    var ints = ['version', 'latest_version', 'issued_at', 'expires_at'];
    if (ints.some(function (k) { return !Number.isSafeInteger(doc[k]) || doc[k] < 0; })) return null;
    if (!STATE_KO[doc.state]) return null;
    if (typeof d.chain_id !== 'string' || !/^(0|[1-9][0-9]{0,77})$/.test(d.chain_id)) return null;
    if (typeof d.verifying_contract !== 'string' || !ADDR.test(d.verifying_contract)) return null;
    var c = { chain_id: d.chain_id, verifying_contract: d.verifying_contract.toLowerCase(), checked_at: Number.isSafeInteger(d.checked_at) ? d.checked_at : null, block_number: typeof d.block_number === 'string' ? d.block_number : null, document: {} };
    hexes.concat(ints).concat(['state']).forEach(function (k) { c.document[k] = doc[k]; });
    c.document.warnings = Array.isArray(doc.warnings) ? doc.warnings.filter(function (x) { return typeof x === 'string'; }) : [];
    // 서버가 기관 정지 여부를 실제로 봤는지: current_state 검사가 PASSED 일 때만(wallet_verification.py:110-127 snapshot_available)
    var cs = (Array.isArray(d.checks) ? d.checks : []).filter(function (x) { return x && x.name === 'current_state'; })[0];
    c.issuer_checked = !!cs && cs.status === 'PASSED';
    c.tx_hash = typeof d.tx_hash === 'string' && HEX32.test(d.tx_hash) ? d.tx_hash : null;
    return c;
  }

  /* ------------------------------ JSON-RPC ------------------------------ */
  function RpcError(kind, detail, data) { this.kind = kind; this.detail = detail; this.data = data; }

  function makeRpc(fetchFn, url, ms) {
    var seq = 0;
    return function rpc(method, params) {
      if (METHODS.indexOf(method) < 0) return Promise.reject(new RpcError('blocked', method + ' 는 부르지 않음'));
      var id = ++seq;
      var ctl = typeof AbortController === 'function' ? new AbortController() : null;
      var timer = null;
      var timeout = new Promise(function (_, rej) { timer = setTimeout(function () { if (ctl) ctl.abort(); rej(new RpcError('timeout', method + ' 시간 초과(' + ms / 1000 + '초)')); }, ms); });
      var req = Promise.resolve().then(function () {
        return fetchFn(url, {
          method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify({ jsonrpc: '2.0', id: id, method: method, params: params }),
          credentials: 'omit', redirect: 'error', cache: 'no-store', signal: ctl ? ctl.signal : undefined
        });
      }).then(function (res) {
        if (!res || res.status !== 200) throw new RpcError('http', method + ' HTTP ' + (res && res.status));
        return res.text();
      }, function (e) {
        if (e instanceof RpcError) throw e;
        throw new RpcError('network', method + ' ' + (e && e.name ? e.name : 'Error'));
      }).then(function (txt) {
        var body;
        try { body = JSON.parse(txt); } catch (e) { throw new RpcError('envelope', method + ' JSON 아님'); }
        if (!body || typeof body !== 'object' || body.jsonrpc !== '2.0' || body.id !== id || (('error' in body) === ('result' in body))) throw new RpcError('envelope', method + ' 응답 모양이 JSON-RPC 와 다름');
        if ('error' in body) {
          var er = body.error || {};
          var data = typeof er.data === 'string' ? er.data : (er.data && typeof er.data.data === 'string' ? er.data.data : '');
          throw new RpcError('rpc_error', method + ' 오류 ' + String(er.code) + ' ' + String(er.message || '').slice(0, 120), data.toLowerCase());
        }
        return body.result;
      });
      return Promise.race([req, timeout]).then(function (r) { clearTimeout(timer); return r; }, function (e) { clearTimeout(timer); throw e; });
    };
  }

  function quantity(v) {
    if (typeof v !== 'string' || !/^0x(0|[1-9a-f][0-9a-f]*)$/.test(v)) throw new RpcError('envelope', '수량 값 형식 아님: ' + String(v).slice(0, 40));
    return BigInt(v).toString();
  }

  // 되돌림(revert) 데이터가 '기록 없음' 오류면 null, 아니면 다시 던짐
  function orMissing(p, errSelector) {
    return p.then(function (r) { return { hex: r }; }, function (e) {
      if (e instanceof RpcError && e.kind === 'rpc_error' && e.data === errSelector) return { missing: true };
      throw e;
    });
  }

  /* ------------------------------ 비교 ------------------------------ */
  function chainStateOf(doc, checkedAt) {
    var s = CHAIN_STATE[doc.state] || ('값 ' + doc.state);
    // 만료는 체인에 따로 없고 계산함: ACTIVE 이고 확인 시각 >= 만료 시각이면 EXPIRED (서버 wallet_verification.py:120 과 같은 규칙)
    if (s === 'ACTIVE' && checkedAt != null && checkedAt >= doc.expiresAt) s = 'EXPIRED';
    return s;
  }
  function ko(s) { return STATE_KO[s] || String(s); }

  function compare(claim, settings, got) {
    var rows = [];
    var checked = [];
    function cmp(label, server, chain, show) {
      checked.push(label);
      if (String(server) !== String(chain)) rows.push({ label: label, server: show ? show(server) : String(server), chain: show ? show(chain) : String(chain) });
    }
    cmp('체인 ID', claim.chain_id, got.chainId);
    cmp('레지스트리 주소', claim.verifying_contract, settings.registry);
    var d = claim.document;
    if (!got.doc) {
      checked.push('문서 기록');
      rows.push({ label: '문서 기록', server: '있음 (버전 ' + d.version + ')', chain: '없음' });
    } else {
      cmp('버전', d.version, got.doc.version);
      cmp('발행 기관 ID', d.issuer_id, got.doc.issuerId);
      cmp('문서 키', d.doc_key, got.doc.docKey);
      cmp('서명 키 ID', d.key_id, got.doc.keyId);
      cmp('원본 해시', d.original_hash, got.doc.originalHash);
      cmp('보호 항목 해시', d.protected_hash, got.doc.protectedHash);
      cmp('내용 형식', d.content_schema, got.doc.contentSchema);
      cmp('발행 시각', d.issued_at, got.doc.issuedAt);
      cmp('만료 시각', d.expires_at, got.doc.expiresAt);
      cmp('상태', d.state, chainStateOf(got.doc, claim.checked_at), ko);
    }
    cmp('최신 버전', d.latest_version, got.latest);
    var serverSusp = d.warnings.indexOf('ISSUER_SUSPENDED') >= 0;
    if (!got.issuer) {
      checked.push('발행 기관');
      rows.push({ label: '발행 기관', server: '등록됨', chain: '없음' });
    } else if (claim.issuer_checked || serverSusp) {
      cmp('발행 기관 상태', serverSusp ? '정지' : '활성', got.issuer.state === 2 ? '정지' : got.issuer.state === 1 ? '활성' : '값 ' + got.issuer.state);
    }
    if (claim.tx_hash) {
      checked.push('거래 영수증');
      var r = got.receipt;
      if (!r) rows.push({ label: '거래 영수증', server: '있음', chain: '없음' });
      else {
        if (r.status !== '1') rows.push({ label: '거래 결과', server: '성공', chain: '실패' });
        if (String(r.to || '').toLowerCase() !== settings.registry) rows.push({ label: '거래 받는 주소', server: settings.registry, chain: String(r.to || '없음') });
      }
    }
    return { rows: rows, checked: checked };
  }

  /* ------------------------------ 결과 ------------------------------ */
  function result(kind, body, extra) {
    var r = { kind: kind, headline: TEXT[kind], tone: TONE[kind], shape: SHAPE[TONE[kind]], body: body, rows: [], checked: [], links: [], raw: [], rpcCalls: 0 };
    for (var k in extra || {}) r[k] = extra[k];
    // 기록관 말풍선: 화면 카드와 같은 내용(머리 문구 + 다른 항목 이름)
    r.say = r.headline + (r.rows.length ? ': ' + r.rows.map(function (x) { return x.label; }).join(', ') : '');
    return r;
  }

  function explorerLinks(chainId, registry, txHash) {
    if (chainId !== SEPOLIA) return [];
    var out = [{ label: 'Etherscan(Sepolia)에서 레지스트리 보기', href: 'https://sepolia.etherscan.io/address/' + registry }];
    if (txHash) out.push({ label: 'Etherscan(Sepolia)에서 거래 보기', href: 'https://sepolia.etherscan.io/tx/' + txHash });
    return out;
  }

  /* verify({ answer, settings, fetch, timeoutMs }) → Promise<result>. 실패해도 reject 하지 않고 판단 보류 결과를 돌려줌 */
  function verify(opts) {
    var a = opts.answer || {};
    var st = normalizeSettings(opts.settings);
    if (a.sample !== false) return Promise.resolve(result('sample', '예시 응답은 체인에 올린 기록이 아니어서 체인에 묻지 않았어요. 값도 지어내지 않았어요.'));
    var missing = [];
    if (!st.rpcUrl) missing.push('체인 RPC 주소');
    if (!st.registry) missing.push('레지스트리 주소');
    if (!st.chainId) missing.push('체인 ID');
    if (missing.length) return Promise.resolve(result('not_configured', '설정에 ' + missing.join('·') + '가 비어 있어 체인에 묻지 않았어요. 설정에서 넣으면 확인할 수 있어요.'));
    var claim = a.chain_claim || null;
    if (!claim) return Promise.resolve(result('no_claim', '서버 응답에 문서 ID·버전 같은 체인 값이 없어 체인에 묻지 않았어요. (문서 ID로 확인한 결과에서만 비교할 수 있어요)'));
    if (typeof opts.fetch !== 'function') return Promise.resolve(result('rpc_fail', '이 브라우저에서 바깥 요청을 보낼 수 없어요.'));

    var calls = 0;
    var raw = [];
    var base = makeRpc(opts.fetch, st.rpcUrl, opts.timeoutMs || TIMEOUT_MS);
    var rpc = function (m, p) { calls++; return base(m, p).then(function (r) { raw.push({ label: m, value: JSON.stringify(p).slice(0, 300) + ' → ' + JSON.stringify(r).slice(0, 900) }); return r; }); };
    var d = claim.document;
    var got = {};
    var fail = function (e) {
      var detail = e instanceof RpcError ? e.detail : (e && e.message ? e.message : String(e));
      raw.push({ label: '실패', value: detail });
      return result('rpc_fail', '체인에서 값을 받지 못했어요. RPC 주소·레지스트리 주소가 맞는지, 노드가 켜져 있는지 확인해 주세요.', { raw: raw, rpcCalls: calls });
    };
    return rpc('eth_chainId', []).then(function (cid) {
      got.chainId = quantity(cid);
      if (got.chainId !== st.chainId) {
        raw.push({ label: '체인 ID', value: '설정 ' + st.chainId + ' · 노드 ' + got.chainId });
        return result('chain_hold', '설정한 체인 ID(' + st.chainId + ')와 RPC 노드의 체인 ID(' + got.chainId + ')가 달라요. 다른 체인의 값과 비교하지 않으려고 멈췄어요.', { raw: raw, rpcCalls: calls });
      }
      var call = function (data) { return rpc('eth_call', [{ to: st.registry, data: data }, 'latest']); };
      return Promise.all([
        orMissing(call(encodeCall('getDocument', [d.document_id, d.version])), SELECTORS.UnknownDocument),
        call(encodeCall('latestVersion', [d.document_id])),
        orMissing(call(encodeCall('getIssuer', [d.issuer_id])), SELECTORS.UnknownIssuer),
        claim.tx_hash ? rpc('eth_getTransactionReceipt', [claim.tx_hash]) : Promise.resolve(null)
      ]).then(function (r) {
        got.doc = r[0].missing ? null : decodeDocument(r[0].hex);
        got.latest = decodeLatestVersion(r[1]);
        got.issuer = r[2].missing ? null : decodeIssuer(r[2].hex);
        if (claim.tx_hash) got.receipt = r[3] ? { status: quantity(r[3].status), to: r[3].to } : null;
        var c = compare(claim, st, got);
        var kind = c.rows.length ? 'mismatch' : 'match';
        var body = kind === 'match'
          ? '서버를 거치지 않고 체인에서 직접 읽은 값이 서버 응답과 같아요. (' + c.checked.length + '개 항목, 최신 블록 기준)'
          : '서버 응답과 체인에서 직접 읽은 값이 다른 항목이 ' + c.rows.length + '개 있어요. (최신 블록 기준)';
        return result(kind, body, { rows: c.rows, checked: c.checked, raw: raw, rpcCalls: calls, links: explorerLinks(got.chainId, st.registry, claim.tx_hash) });
      });
    }).catch(fail);
  }

  return {
    SELECTORS: SELECTORS, METHODS: METHODS, TEXT: TEXT, KEY: KEY, SEPOLIA: SEPOLIA,
    checkRpcUrl: checkRpcUrl, checkRegistry: checkRegistry, checkChainId: checkChainId,
    normalizeSettings: normalizeSettings, createStore: createStore,
    encodeCall: encodeCall, decodeDocument: decodeDocument, decodeLatestVersion: decodeLatestVersion, decodeIssuer: decodeIssuer,
    encUint: encUint, claimFrom: claimFrom, compare: compare, explorerLinks: explorerLinks, verify: verify
  };
});
