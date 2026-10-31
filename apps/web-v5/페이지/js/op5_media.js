/* 5안 첨부 입력 검사 — 문서 사진(이미지)·음성(PCM WAV)을 서버에 보내기 전에 브라우저에서 먼저 확인한다.
   기준은 D(#94) 분석기 규칙과 같다: services/analyzer/src/originproof_analyzer/audio_inputs.py(inspect_pcm_wav),
   fixtures/synthetic/media_safety_v1/manifest.json(조건 24종), docs/handoffs/v5_d_media_validation_20261023.md.
   - 이미지: PNG·JPEG·WebP, 5MB 이하, 한 장(움직이는 이미지 아님), 내용과 형식 일치
   - 음성: PCM WAV, 20MiB·300초 이하, 1~2채널, 8/16/24/32비트 정수
   결과 상태: ok(보낼 수 있음) · low(인식 부족 우려) · unsupported(미지원) · failed(파일 손상)
   서버 업로드 경로(C 계약)가 아직 없으므로 검사만 하고 보내지 않는다. 글자 읽기·받아쓰기 결과를 지어내지 않는다. */
(function (root) {
  'use strict';
  var IMG_MAX = 5 * 1024 * 1024, WAV_MAX = 20 * 1024 * 1024, WAV_SEC = 300;
  var IMG_TYPES = { 'image/png': 'png', 'image/jpeg': 'jpeg', 'image/webp': 'webp' };

  function r(kind, state, code, title, advice, extra) {
    var o = { kind: kind, state: state, code: code, title: title, advice: advice };
    if (extra) for (var k in extra) o[k] = extra[k];
    return o;
  }
  function bytes(file, n) { return file.slice(0, n).arrayBuffer().then(function (b) { return new Uint8Array(b); }); }
  function sniff(u) {
    if (u.length >= 8 && u[0] === 0x89 && u[1] === 0x50 && u[2] === 0x4e && u[3] === 0x47) return 'png';
    if (u.length >= 3 && u[0] === 0xff && u[1] === 0xd8 && u[2] === 0xff) return 'jpeg';
    if (u.length >= 12 && str(u, 0, 4) === 'RIFF' && str(u, 8, 4) === 'WEBP') return 'webp';
    if (u.length >= 12 && str(u, 0, 4) === 'RIFF' && str(u, 8, 4) === 'WAVE') return 'wav';
    if (u.length >= 3 && str(u, 0, 3) === 'ID3') return 'mp3';
    if (u.length >= 2 && u[0] === 0xff && (u[1] & 0xe0) === 0xe0) return 'mp3';
    if (u.length >= 8 && str(u, 4, 4) === 'ftyp') return 'm4a';
    if (u.length >= 4 && str(u, 0, 4) === '%PDF') return 'pdf';
    return '';
  }
  function str(u, at, n) { var s = ''; for (var i = 0; i < n && at + i < u.length; i++) s += String.fromCharCode(u[at + i]); return s; }
  function hasChunk(u, name) { // PNG acTL(움직이는 PNG) 찾기
    for (var i = 8; i + 8 <= u.length;) {
      var len = (u[i] << 24 | u[i + 1] << 16 | u[i + 2] << 8 | u[i + 3]) >>> 0;
      var t = str(u, i + 4, 4);
      if (t === name) return true;
      if (t === 'IDAT' || t === 'IEND') return false;
      i += 12 + len;
    }
    return false;
  }
  function jpegOrientation(u) {
    for (var i = 2; i + 4 < u.length;) {
      if (u[i] !== 0xff) return 0;
      var m = u[i + 1], len = u[i + 2] << 8 | u[i + 3];
      if (m === 0xe1 && str(u, i + 4, 4) === 'Exif') {
        var t = i + 10, le = str(u, t, 2) === 'II';
        var g16 = function (p) { return le ? u[p] | u[p + 1] << 8 : u[p] << 8 | u[p + 1]; };
        var g32 = function (p) { return le ? (u[p] | u[p + 1] << 8 | u[p + 2] << 16 | u[p + 3] << 24) >>> 0 : (u[p] << 24 | u[p + 1] << 16 | u[p + 2] << 8 | u[p + 3]) >>> 0; };
        var ifd = t + g32(t + 4), n = g16(ifd);
        for (var k = 0; k < n; k++) { var e = ifd + 2 + k * 12; if (g16(e) === 0x0112) return g16(e + 8); }
        return 0;
      }
      i += 2 + len;
    }
    return 0;
  }
  function decode(file) {
    return new Promise(function (ok) {
      var url = URL.createObjectURL(file), img = new Image();
      img.onload = function () { ok({ img: img, url: url }); };
      img.onerror = function () { URL.revokeObjectURL(url); ok(null); };
      img.src = url;
    });
  }
  function quality(img) { // 밝기 대비(표준편차)와 선명도(라플라시안 분산)를 작은 크기로 계산
    var w = Math.min(320, img.naturalWidth), h = Math.max(1, Math.round(img.naturalHeight * w / img.naturalWidth));
    var c = document.createElement('canvas'); c.width = w; c.height = h;
    var g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0, w, h);
    var d = g.getImageData(0, 0, w, h).data, L = new Float32Array(w * h), sum = 0;
    for (var i = 0; i < w * h; i++) { L[i] = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2]; sum += L[i]; }
    var mean = sum / (w * h), v = 0;
    for (i = 0; i < w * h; i++) v += (L[i] - mean) * (L[i] - mean);
    var sd = Math.sqrt(v / (w * h)), lap = [], lm = 0;
    for (var y = 1; y < h - 1; y++) for (var x = 1; x < w - 1; x++) {
      var p = y * w + x, q = 4 * L[p] - L[p - 1] - L[p + 1] - L[p - w] - L[p + w]; lap.push(q); lm += q;
    }
    lm /= Math.max(1, lap.length); var lv = 0;
    for (i = 0; i < lap.length; i++) lv += (lap[i] - lm) * (lap[i] - lm);
    return { contrast: sd, sharp: lap.length ? lv / lap.length : 0 };
  }

  function inspectImage(file, kindByHead) {
    var K = 'DOCUMENT_IMAGE', declared = IMG_TYPES[file.type];
    if (!declared) return Promise.resolve(r(K, 'unsupported', 'UNSUPPORTED_INPUT', '이 그림 형식은 아직 못 읽어요', 'PNG·JPG·WebP 사진(화면 캡처)으로 올려 주세요.'));
    if (file.size === 0) return Promise.resolve(r(K, 'failed', 'MALFORMED_INPUT', '빈 파일이에요', '사진을 다시 찍거나 다시 저장해서 올려 주세요.'));
    if (file.size > IMG_MAX) return Promise.resolve(r(K, 'unsupported', 'MALFORMED_INPUT', '사진이 5MB보다 커요', '화면을 캡처하거나 크기를 줄여서 올려 주세요.'));
    return bytes(file, 65536).then(function (head) {
      var real = sniff(head);
      if (real !== declared) return r(K, 'failed', 'MALFORMED_INPUT', '파일 이름(형식)과 실제 내용이 달라요', '휴대폰 사진 앱에서 다시 저장하거나 화면을 캡처해서 올려 주세요.');
      if (real === 'png' && hasChunk(head, 'acTL')) return r(K, 'unsupported', 'MALFORMED_INPUT', '움직이는 그림은 읽을 수 없어요', '안내문이 보이는 화면 한 장만 캡처해서 올려 주세요.');
      var orient = real === 'jpeg' ? jpegOrientation(head) : 0;
      return decode(file).then(function (dec) {
        if (!dec) return r(K, 'failed', 'MALFORMED_INPUT', '사진 파일이 깨져 있어요', '사진을 다시 찍거나 다시 내려받아 올려 주세요.');
        var img = dec.img, w = img.naturalWidth, h = img.naturalHeight, q = quality(img);
        URL.revokeObjectURL(dec.url);
        var size = { width: w, height: h, contrast: Math.round(q.contrast), sharp: Math.round(q.sharp) };
        if (Math.min(w, h) < 200) return r(K, 'low', 'LOW_RECOGNITION', '사진이 너무 작아 글자를 못 읽을 수 있어요', '안내문이 화면에 크게 보이게 다시 캡처해 주세요.', size);
        if (q.contrast < 25) return r(K, 'low', 'LOW_RECOGNITION', '글자와 배경이 비슷해 흐리게 보여요', '밝은 곳에서 다시 찍거나 화면 밝기를 올려 캡처해 주세요.', size);
        if (q.sharp < 40) return r(K, 'low', 'LOW_RECOGNITION', '사진이 흐려서 글자를 못 읽을 수 있어요', '흔들리지 않게 다시 찍어 주세요.', size);
        if (orient > 1) return r(K, 'ok', 'READY_ROTATED', '보낼 수 있어요(사진이 돌아가 있어요)', '읽을 때 방향을 바로잡아요. 바로 세워 찍으면 더 정확해요.', size);
        return r(K, 'ok', 'READY', '읽을 준비가 됐어요', '실서버 모드에서 글자를 읽어 확인해요.', size);
      });
    });
  }

  function inspectWav(file) {
    var K = 'AUDIO';
    if (file.size === 0) return Promise.resolve(r(K, 'failed', 'MALFORMED_INPUT', '빈 녹음 파일이에요', '다시 녹음해서 올려 주세요.'));
    if (file.size > WAV_MAX) return Promise.resolve(r(K, 'unsupported', 'MALFORMED_INPUT', '녹음 파일이 20MB보다 커요', '5분 이내로 나눠서 올려 주세요.'));
    return file.arrayBuffer().then(function (buf) {
      var u = new Uint8Array(buf), dv = new DataView(buf);
      if (sniff(u) !== 'wav') return r(K, 'failed', 'MALFORMED_INPUT', '파일 이름(형식)과 실제 내용이 달라요', 'WAV로 다시 저장해서 올려 주세요.');
      if (dv.getUint32(4, true) + 8 !== u.length) return r(K, 'failed', 'MALFORMED_INPUT', '녹음 파일이 잘렸거나 손상됐어요', '녹음 앱에서 다시 저장해서 올려 주세요.');
      var fmt = null, data = null, seen = {};
      for (var p = 12; p + 8 <= u.length;) {
        var id = str(u, p, 4), len = dv.getUint32(p + 4, true);
        if (p + 8 + len > u.length) return r(K, 'failed', 'MALFORMED_INPUT', '녹음 파일이 잘렸거나 손상됐어요', '녹음 앱에서 다시 저장해서 올려 주세요.');
        if ((id === 'fmt ' || id === 'data') && seen[id]) return r(K, 'failed', 'MALFORMED_INPUT', '녹음 파일 구조가 이상해요', '녹음 앱에서 다시 저장해서 올려 주세요.');
        seen[id] = 1;
        if (id === 'fmt ') fmt = { at: p + 8, len: len };
        if (id === 'data') data = { at: p + 8, len: len };
        p += 8 + len + (len & 1);
      }
      if (!fmt || !data) return r(K, 'failed', 'MALFORMED_INPUT', '녹음 파일 구조가 이상해요', '녹음 앱에서 다시 저장해서 올려 주세요.');
      var tag = dv.getUint16(fmt.at, true), ch = dv.getUint16(fmt.at + 2, true), rate = dv.getUint32(fmt.at + 4, true),
        brate = dv.getUint32(fmt.at + 8, true), align = dv.getUint16(fmt.at + 12, true), bits = dv.getUint16(fmt.at + 14, true);
      if (tag === 0xfffe && fmt.len >= 40) {
        var mask = dv.getUint32(fmt.at + 20, true), sub = dv.getUint16(fmt.at + 24, true);
        if (sub !== 1) return r(K, 'unsupported', 'UNSUPPORTED_INPUT', '이 녹음 형식은 아직 못 읽어요', '일반(PCM) WAV로 다시 저장해 주세요.');
        var bitsSet = 0; for (var m = mask; m; m >>>= 1) bitsSet += m & 1;
        if (mask && bitsSet !== ch) return r(K, 'failed', 'MALFORMED_INPUT', '녹음 파일 정보가 서로 맞지 않아요', '녹음 앱에서 다시 저장해서 올려 주세요.');
      } else if (tag !== 1) return r(K, 'unsupported', 'UNSUPPORTED_INPUT', '이 녹음 형식은 아직 못 읽어요', '일반(PCM) WAV로 다시 저장해 주세요.');
      if (ch < 1 || ch > 2) return r(K, 'unsupported', 'UNSUPPORTED_INPUT', '채널이 너무 많아요(2개까지)', '모노나 스테레오로 다시 저장해 주세요.');
      if ([8, 16, 24, 32].indexOf(bits) < 0 || !rate || align !== ch * bits / 8 || brate !== rate * align)
        return r(K, 'failed', 'MALFORMED_INPUT', '녹음 파일 정보가 서로 맞지 않아요', '녹음 앱에서 다시 저장해서 올려 주세요.');
      if (data.len % align) return r(K, 'failed', 'MALFORMED_INPUT', '녹음 끝부분이 잘렸어요', '녹음 앱에서 다시 저장해서 올려 주세요.');
      var frames = data.len / align, sec = frames / rate;
      if (frames > WAV_SEC * rate) return r(K, 'unsupported', 'MALFORMED_INPUT', '녹음이 5분보다 길어요', '5분 이내로 나눠서 올려 주세요.');
      if (!frames) return r(K, 'failed', 'MALFORMED_INPUT', '녹음 안에 소리가 없어요', '다시 녹음해서 올려 주세요.');
      var peak = 0, step = Math.max(1, Math.floor(frames / 20000)), bps = bits / 8;
      for (var f = 0; f < frames; f += step) {
        var o = data.at + f * align, s;
        if (bits === 8) s = (u[o] - 128) / 128; else if (bits === 16) s = dv.getInt16(o, true) / 32768;
        else if (bits === 24) s = ((u[o] | u[o + 1] << 8 | u[o + 2] << 16) << 8 >> 8) / 8388608; else s = dv.getInt32(o, true) / 2147483648;
        peak = Math.max(peak, Math.abs(s));
      }
      var info = { seconds: Math.round(sec * 10) / 10, channels: ch, bits: bits, rate: rate };
      if (peak < 0.01) return r(K, 'low', 'LOW_RECOGNITION', '소리가 거의 없어요', '휴대폰을 입 가까이 두고 다시 녹음해 주세요.', info);
      if (peak > 0.999) return r(K, 'low', 'LOW_RECOGNITION', '소리가 너무 커서 찢어졌어요', '조금 떨어져서 다시 녹음해 주세요. 그대로 보내면 잘못 들을 수 있어요.', info);
      return r(K, 'ok', 'READY', '들을 준비가 됐어요(' + info.seconds + '초)', '말소리인지, 무슨 말인지는 서버 연결 뒤 받아쓰기로 확인해요.', info);
    });
  }

  function inspect(file) {
    var name = (file.name || '').toLowerCase();
    if (file.type in IMG_TYPES || /\.(png|jpe?g|webp)$/.test(name)) return inspectImage(file);
    // 입력은 글·이미지 두 가지만(3회차 멘토링 반영, 2026-10-26). 음성·PDF는 받지 않는다(inspectWav 는 나중을 위해 남김)
    if (/^audio\//.test(file.type) || /\.(wav|mp3|m4a|aac|ogg)$/.test(name)) return Promise.resolve(r('AUDIO', 'unsupported', 'UNSUPPORTED_INPUT', '음성은 받지 않아요', '받은 내용을 글로 붙여 넣거나, 안내문 화면을 사진(캡처)으로 올려 주세요.'));
    if (file.type === 'application/pdf' || /\.pdf$/.test(name)) return Promise.resolve(r('DOCUMENT', 'unsupported', 'UNSUPPORTED_INPUT', 'PDF는 받지 않아요', '안내문이 보이는 화면을 사진(캡처)으로 올려 주세요.'));
    if (file.type === 'text/plain' || /\.txt$/.test(name)) return Promise.resolve(r('TEXT', 'ok', 'READY', '글 파일이에요', '내용을 복사해서 채팅칸에 붙여 넣으면 바로 확인해요.'));
    return Promise.resolve(r('OTHER', 'unsupported', 'UNSUPPORTED_INPUT', '이 파일은 받을 수 없어요', '글은 채팅칸에 붙여 넣고, 문서는 사진(PNG·JPG·WebP)으로 올려 주세요.'));
  }

  /* 서버 연결 뒤 받을 실패 코드 → 쉬운 말(C 업로드 계약·D 분석기 오류 경계 기준). 업로드 경로가 생기면 그대로 쓴다. */
  var SERVER_FAIL = {
    UNSUPPORTED_INPUT: '이 형식은 아직 못 읽어요.',
    MALFORMED_INPUT: '파일이 손상됐거나 너무 커요.',
    INCOMPLETE_OUTPUT: '일부만 읽혀서 결과를 내지 않았어요. 더 선명한 사진이나 조용한 곳의 녹음으로 다시 해 주세요.',
    TIMEOUT: '읽는 데 시간이 너무 걸려 멈췄어요. 잠시 뒤 다시 해 주세요.',
    ANALYZER_UNAVAILABLE: '지금은 읽는 기능이 연결돼 있지 않아요.',
    HTTP_413: '파일이 너무 커요.', HTTP_415: '이 형식은 받을 수 없어요.', HTTP_422: '파일 내용을 확인할 수 없어요.', HTTP_429: '요청이 많아요. 잠시 뒤 다시 해 주세요.'
  };

  root.OP5Media = { inspect: inspect, SERVER_FAIL: SERVER_FAIL, LIMITS: { IMG_MAX: IMG_MAX, WAV_MAX: WAV_MAX, WAV_SEC: WAV_SEC } };
})(typeof window !== 'undefined' ? window : globalThis);
