import { build } from 'esbuild';
import { execFileSync } from 'node:child_process';
import { readdirSync, copyFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('.', import.meta.url));
// 5안: 빌드 결과는 ../페이지/ 에만 둔다(보는 파일과 소스 분리)
const out = fileURLToPath(new URL('../페이지/', import.meta.url));
for (const [entry, name] of [['sidebar-entry.tsx','sidebar'], ['business-entry.tsx','business'], ['admin-entry.tsx','admin']]) {
 await build({absWorkingDir:root,entryPoints:[entry],bundle:true,minify:true,jsx:'automatic',alias:{'@':root},outfile:out+name+'.bundle.js'});
 execFileSync(root+'node_modules/.bin/tailwindcss',['-i',root+name+'.css','-o',out+name+'.bundle.css','--minify'],{stdio:'inherit',cwd:root});
}
// 페이지의 ES 모듈(auth.js 등)도 쓰는 공용 API 도우미(api-client.js·w3-input.js)만 페이지 폴더로 복사
for (const f of ['api-client.js','w3-input.js']) copyFileSync(root+f, out+f);
