// PNG 두 장 픽셀 비교 (감사팀 재작업 T5). Node 표준 zlib 으로 디코드(설치 없음).
// 사용: node 개발/png-diff.mjs <기준.png> <비교.png>
// 출력: 두 파일 크기, 다른 픽셀 수 / 전체, 비율. RGBA 네 값 중 하나라도 다르면 "다른 픽셀".
// 종료 코드: 0 = 같음(다른 픽셀 0) · 1 = 다른 픽셀 있음 · 2 = 크기 다름(실패) · 3 = 읽기/형식 오류
// 지원: 8비트(그레이·RGB·팔레트·그레이+알파·RGBA), 팔레트 1·2·4비트, 16비트(상위 바이트로 비교). 인터레이스 PNG 는 오류로 끝냄.
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SIG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const CHANNELS = { 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 };

export function decodePng(buf) {
  if (!Buffer.isBuffer(buf) || buf.length < 33 || !buf.subarray(0, 8).equals(SIG)) throw new Error('PNG 파일이 아니에요');
  let off = 8, ihdr = null, plte = null, trns = null;
  const idat = [];
  while (off + 8 <= buf.length) {
    const len = buf.readUInt32BE(off), type = buf.toString('latin1', off + 4, off + 8);
    if (off + 12 + len > buf.length) throw new Error('PNG 조각 길이가 파일보다 길어요');
    const data = buf.subarray(off + 8, off + 8 + len);
    if (type === 'IHDR') ihdr = { width: data.readUInt32BE(0), height: data.readUInt32BE(4), depth: data[8], color: data[9], interlace: data[12] };
    else if (type === 'PLTE') plte = data;
    else if (type === 'tRNS') trns = data;
    else if (type === 'IDAT') idat.push(data);
    else if (type === 'IEND') break;
    off += 12 + len;
  }
  if (!ihdr) throw new Error('IHDR 가 없어요');
  const { width, height, depth, color, interlace } = ihdr;
  const ch = CHANNELS[color];
  if (!ch) throw new Error('알 수 없는 색 형식 ' + color);
  if (interlace) throw new Error('인터레이스 PNG 는 지원하지 않아요');
  if (!(depth === 8 || depth === 16 || (color === 3 && [1, 2, 4].includes(depth)))) throw new Error(`지원하지 않는 비트 수 ${depth}(색 형식 ${color})`);
  if (color === 3 && !plte) throw new Error('팔레트가 없어요');
  if (!width || !height || width * height > 100e6) throw new Error('크기가 이상해요');
  const raw = zlib.inflateSync(Buffer.concat(idat));
  const bpp = Math.max(1, (ch * depth) >> 3);           // 필터 기준 바이트
  const stride = Math.ceil((width * ch * depth) / 8);
  if (raw.length < (stride + 1) * height) throw new Error('이미지 데이터가 모자라요');
  const out = Buffer.alloc(width * height * 4);
  let prev = Buffer.alloc(stride), cur = Buffer.alloc(stride);
  for (let y = 0; y < height; y++) {
    const ft = raw[y * (stride + 1)], line = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1));
    for (let i = 0; i < stride; i++) {
      const a = i >= bpp ? cur[i - bpp] : 0, b = prev[i], c = i >= bpp ? prev[i - bpp] : 0;
      let v;
      switch (ft) {
        case 0: v = 0; break;
        case 1: v = a; break;
        case 2: v = b; break;
        case 3: v = (a + b) >> 1; break;
        case 4: { const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c); v = pa <= pb && pa <= pc ? a : pb <= pc ? b : c; break; }
        default: throw new Error(`알 수 없는 필터 ${ft}(줄 ${y})`);
      }
      cur[i] = (line[i] + v) & 0xff;
    }
    for (let x = 0; x < width; x++) {
      const o = (y * width + x) * 4;
      if (color === 3) {
        const per = 8 / depth, byte = cur[Math.floor(x / per)], shift = 8 - depth * ((x % per) + 1);
        const idx = depth === 8 ? cur[x] : (byte >> shift) & ((1 << depth) - 1);
        if (idx * 3 + 2 >= plte.length) throw new Error('팔레트 밖 색 번호');
        out[o] = plte[idx * 3]; out[o + 1] = plte[idx * 3 + 1]; out[o + 2] = plte[idx * 3 + 2];
        out[o + 3] = trns && idx < trns.length ? trns[idx] : 255;
      } else {
        const s = depth === 16 ? 2 : 1, base = x * ch * s, g = (k) => cur[base + k * s];
        if (color === 0) { out[o] = out[o + 1] = out[o + 2] = g(0); out[o + 3] = 255; }
        else if (color === 4) { out[o] = out[o + 1] = out[o + 2] = g(0); out[o + 3] = g(1); }
        else if (color === 2) { out[o] = g(0); out[o + 1] = g(1); out[o + 2] = g(2); out[o + 3] = 255; }
        else { out[o] = g(0); out[o + 1] = g(1); out[o + 2] = g(2); out[o + 3] = g(3); }
      }
    }
    [prev, cur] = [cur, prev];
  }
  return { width, height, rgba: out };
}

export function comparePng(a, b) {
  if (a.width !== b.width || a.height !== b.height) return { sameSize: false, diff: null, total: null };
  let diff = 0;
  for (let i = 0; i < a.rgba.length; i += 4)
    if (a.rgba[i] !== b.rgba[i] || a.rgba[i + 1] !== b.rgba[i + 1] || a.rgba[i + 2] !== b.rgba[i + 2] || a.rgba[i + 3] !== b.rgba[i + 3]) diff++;
  return { sameSize: true, diff, total: a.width * a.height };
}

export function main(argv, print = console.log) {
  if (argv.length !== 2) { print('사용: node 개발/png-diff.mjs <기준.png> <비교.png>'); return 3; }
  let A, B;
  try { A = decodePng(fs.readFileSync(argv[0])); B = decodePng(fs.readFileSync(argv[1])); }
  catch (e) { print('읽기 실패: ' + e.message); return 3; }
  print(`기준 ${path.basename(argv[0])}: ${A.width}×${A.height}`);
  print(`비교 ${path.basename(argv[1])}: ${B.width}×${B.height}`);
  const r = comparePng(A, B);
  if (!r.sameSize) { print('판정: 실패(크기가 달라 비교하지 않음)'); return 2; }
  print(`다른 픽셀: ${r.diff} / ${r.total} (${((r.diff / r.total) * 100).toFixed(4)}%)`);
  print(r.diff === 0 ? '판정: 통과(다른 픽셀 0)' : '판정: 다름');
  return r.diff === 0 ? 0 : 1;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exit(main(process.argv.slice(2)));
