// T5 픽셀 비교 스크립트 자기시험(설치 없음). 시험용 PNG 는 메모리에서 zlib 으로 만들고 파일은 기존 캡처만 읽음.
//   node --test 시험/png_diff.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import zlib from 'node:zlib';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { decodePng, comparePng, main } from '../개발/png-diff.mjs';


function crc32(buf) { let c, crc = 0xffffffff; for (const b of buf) { c = (crc ^ b) & 0xff; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; crc = (crc >>> 8) ^ c; } return (crc ^ 0xffffffff) >>> 0; }
function chunk(type, data) { const len = Buffer.alloc(4); len.writeUInt32BE(data.length); const td = Buffer.concat([Buffer.from(type, 'latin1'), data]); const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(td)); return Buffer.concat([len, td, crc]); }
// RGBA 8비트 PNG, 줄마다 필터 종류를 돌려가며 인코딩(0~4 모두 시험)
function encodeRgba(w, h, px) {
  const stride = w * 4, rows = [];
  let prev = Buffer.alloc(stride);
  for (let y = 0; y < h; y++) {
    const cur = px.subarray(y * stride, (y + 1) * stride), ft = y % 5, line = Buffer.alloc(stride + 1);
    line[0] = ft;
    for (let i = 0; i < stride; i++) {
      const a = i >= 4 ? cur[i - 4] : 0, b = prev[i], c = i >= 4 ? prev[i - 4] : 0;
      const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
      const pred = [0, a, b, (a + b) >> 1, pa <= pb && pa <= pc ? a : pb <= pc ? b : c][ft];
      line[i + 1] = (cur[i] - pred) & 0xff;
    }
    rows.push(line); prev = Buffer.from(cur);
  }
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 6;
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(Buffer.concat(rows))), chunk('IEND', Buffer.alloc(0))]);
}
function pattern(w, h, seed = 1) { const b = Buffer.alloc(w * h * 4); for (let i = 0; i < b.length; i++) b[i] = (i * 37 + seed * 101 + (i >> 3) * 13) & 0xff; return b; }
const quiet = () => {};
// Portable CLI file-I/O fixtures; these are synthetic PNGs, not website screenshots.
const CAP = fs.mkdtempSync(path.join(os.tmpdir(), 'originproof-png-cli-'));
const DARK = path.join(CAP, 'synthetic-a.png'), LIGHT = path.join(CAP, 'synthetic-b.png');
const SMALL = path.join(CAP, 'synthetic-small.png');
fs.writeFileSync(DARK, encodeRgba(7, 10, pattern(7, 10, 1)));
fs.writeFileSync(LIGHT, encodeRgba(7, 10, pattern(7, 10, 2)));
fs.writeFileSync(SMALL, encodeRgba(3, 4, pattern(3, 4, 1)));
test.after(() => fs.rmSync(CAP, { recursive: true, force: true }));


test('디코드: 필터 0~4 를 모두 쓴 PNG 를 원래 픽셀로 되돌림', () => {
  const px = pattern(7, 10);
  const d = decodePng(encodeRgba(7, 10, px));
  assert.equal(d.width, 7); assert.equal(d.height, 10);
  assert.ok(d.rgba.equals(px));
});

test('비교: 같은 그림 0, 한 픽셀 바꾸면 1, 크기 다르면 sameSize false', () => {
  const px = pattern(6, 5), q = Buffer.from(px); q[4 * 7 + 2] ^= 1;
  assert.equal(comparePng(decodePng(encodeRgba(6, 5, px)), decodePng(encodeRgba(6, 5, px))).diff, 0);
  assert.equal(comparePng(decodePng(encodeRgba(6, 5, px)), decodePng(encodeRgba(6, 5, q))).diff, 1);
  assert.equal(comparePng(decodePng(encodeRgba(6, 5, px)), decodePng(encodeRgba(5, 6, pattern(5, 6)))).sameSize, false);
});

test('CLI 파일 I/O(합성 PNG): 같은 파일 = 다른 픽셀 0(종료 0), 다른 파일 > 0(종료 1)', () => {
  const lines = [];
  assert.equal(main([DARK, DARK], (s) => lines.push(s)), 0);
  assert.ok(lines.some((s) => /다른 픽셀: 0 \//.test(s)));
  const l2 = [];
  assert.equal(main([DARK, LIGHT], (s) => l2.push(s)), 1);
  const n = Number(/다른 픽셀: (\d+)/.exec(l2.join('\n'))[1]);
  assert.ok(n > 0);
});

test('PNG 가 아니거나 인수 개수가 틀리면 종료 3', () => {
  assert.equal(main([fileURLToPath(import.meta.url), DARK], quiet), 3);
  assert.equal(main([DARK], quiet), 3);
  assert.throws(() => decodePng(Buffer.from('not png')), /PNG/);
});

test('크기가 다르면 실패 종료(2)', () => {
  // Same decoder/CLI, intentionally different synthetic dimensions.
  const lines = [];
  assert.equal(main([DARK, SMALL], (s) => lines.push(s)), 2);
  assert.ok(lines.some((s) => /실패/.test(s)));
  const tiny = decodePng(encodeRgba(1, 1, Buffer.from([0, 0, 0, 255])));
  assert.equal(comparePng(decodePng(fs.readFileSync(DARK)), tiny).sameSize, false);
});
