import path from "node:path";
import {fileURLToPath} from "node:url";
import type { NextConfig } from "next";

const apiOrigin = process.env.ORIGINPROOF_API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../.."),
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiOrigin}/:path*`,
      },
    ];
  },
};

export default nextConfig;
