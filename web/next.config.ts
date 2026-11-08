import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  experimental: {
    proxyTimeout: 300_000, // 5分。LLMの応答を待てるようにする
  },
  async rewrites() {
    // ブラウザ → Next.js(/api/...) → FastAPI(:8000) と中継する
    return [{ source: "/api/:path*", destination: "http://127.0.0.1:8000/:path*" }];
  },
};

export default nextConfig;

