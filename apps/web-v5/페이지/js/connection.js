/* 설정 저장소 + 연결(모드·서버 주소·어댑터 고르기) + 기록 다시 보기.
   화면(DOM)을 만지지 않아서 node 에서 가짜 저장소·가짜 fetch 로 시험함(tools/connection.test.js).
   - 모드: 'sample'(예시로 보기) / 'api'(실제 서버 연결). 실제 연결이 실패해도 모드를 저절로 바꾸지 않음.
   - 서버 주소: text_tools.js normalizeServerUrl 로 정리, 이 컴퓨터 주소(127.0.0.1·localhost·[::1])만 받음.
   - 기록 다시 보기: 저장해 둔 가린 결과(스냅샷)나 예시만 씀. 서버를 다시 부르지 않음(fetch 0회). */
(function () {
  'use strict';
  var Hk = (window.Hk = window.Hk || {});
  function T() { return Hk.text; }

  var BAD_URL = '서버 주소 형식이 맞지 않아요. 예: http://127.0.0.1:8000';
  var NOT_LOCAL = '지금은 이 컴퓨터 주소(127.0.0.1·localhost)로만 연결할 수 있어요.';

  /* 설정 저장소: get() 은 늘 같은 객체, save() 는 정리(normalize)한 뒤 그 객체에 다시 담아 저장 */
  function createSettingsStore(storage) {
    var prefs = T().parseSettings(T().storageGet(storage, T().KEYS.settings));
    function save() {
      var n = T().normalizeSettings(prefs);
      Object.keys(n).forEach(function (k) { prefs[k] = n[k]; });
      return T().storageSet(storage, T().KEYS.settings, JSON.stringify(n));
    }
    return { get: function () { return prefs; }, save: save };
  }

  /* opts: { store, fetch, viaProxy, sample, createApi, checkConnection } (뒤의 셋은 시험에서 바꿔 넣을 수 있음) */
  function createConnection(opts) {
    var store = opts.store;
    var sample = opts.sample || Hk.sampleAdapter;
    var createApi = opts.createApi || Hk.createApiAdapter;
    var checkConn = opts.checkConnection || Hk.checkConnection;
    var api = null;

    function prefs() { return store.get(); }
    function mode() { return prefs().mode === 'api' ? 'api' : 'sample'; }
    function serverUrl() { return prefs().serverUrl; }

    function setMode(m) {
      if (m !== 'api' && m !== 'sample') return mode();
      prefs().mode = m;
      store.save();
      return mode();
    }

    // 돌려줌 { ok, value, message }. 틀린 주소는 저장하지 않고 이전 주소를 그대로 씀
    function setServerUrl(raw) {
      var n = T().normalizeServerUrl(typeof raw === 'string' ? raw : '');
      if (!n) return { ok: false, value: serverUrl(), message: BAD_URL };
      if (Hk.api && !Hk.api.isLoopback(n)) return { ok: false, value: serverUrl(), message: NOT_LOCAL };
      prefs().serverUrl = n;
      store.save();
      api = null;
      return { ok: true, value: n, message: '' };
    }

    function apiAdapter() {
      if (!api || api.serverUrl !== serverUrl()) api = createApi({ fetch: opts.fetch, serverUrl: serverUrl(), viaProxy: !!opts.viaProxy });
      return api;
    }
    function adapter() { return mode() === 'api' ? apiAdapter() : sample; }

    // check(text, { onStaff }): 모드에 맞는 어댑터로. 예시 어댑터는 onStaff 를 쓰지 않음(app.js 가 순서대로 그림)
    function check(text, o) { return adapter().check(text, o); }

    function testConnection() {
      return checkConn({ fetch: opts.fetch, serverUrl: serverUrl(), viaProxy: !!opts.viaProxy });
    }

    // 기록 다시 보기: 스냅샷 → 예시 → (옛 기록) 가린 글을 예시 어댑터로. 어느 경우도 서버를 부르지 않음
    function restore(entry) {
      if (!entry) return Promise.resolve(null);
      if (entry.snapshot) {
        var snap = T().cleanSnapshot(entry.snapshot);
        if (snap) return Promise.resolve(snap);
      }
      if (entry.sampleId) return Promise.resolve(sample.get(entry.sampleId));
      if (entry.text) return sample.check(entry.text);
      return Promise.resolve(null);
    }

    return { mode: mode, setMode: setMode, serverUrl: serverUrl, setServerUrl: setServerUrl, adapter: adapter, check: check, testConnection: testConnection, restore: restore };
  }

  Hk.createSettingsStore = createSettingsStore;
  Hk.createConnection = createConnection;
})();
