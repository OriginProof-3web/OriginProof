import { FlatCompat } from "@eslint/eslintrc";
import { fileURLToPath } from "node:url";
import path from "node:path";

const baseDirectory = path.dirname(fileURLToPath(import.meta.url));
const compat = new FlatCompat({ baseDirectory });

const config = [
  { ignores: [".next/**", "public/**", "official/node_modules/**", "node_modules/**", "playwright-report/**", "test-results/**"] },
  ...compat.extends("next/core-web-vitals"),
];

export default config;
