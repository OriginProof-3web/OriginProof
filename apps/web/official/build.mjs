import { build } from 'esbuild';
import { execFileSync } from 'node:child_process';
import { readdirSync, copyFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('.', import.meta.url));
const out = fileURLToPath(new URL('../public/', import.meta.url));
for (const [entry, name] of [['sidebar-entry.tsx','sidebar'], ['business-entry.tsx','business'], ['admin-entry.tsx','admin']]) {
 await build({absWorkingDir:root,entryPoints:[entry],bundle:true,minify:true,jsx:'automatic',alias:{'@':root},outfile:out+name+'.bundle.js'});
 execFileSync(root+'node_modules/.bin/tailwindcss',['-i',root+name+'.css','-o',out+name+'.bundle.css','--minify'],{stdio:'inherit',cwd:root});
}
for (const name of readdirSync(root)) {
 if (/\.(html|css|js)$/.test(name) && !name.endsWith('.test.js')) copyFileSync(root+name,out+name);
}
