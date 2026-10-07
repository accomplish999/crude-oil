import type { NextConfig } from "next";

const rawBase = process.env.NEXT_PUBLIC_BASE_PATH?.trim() ?? "";
const basePath = rawBase === "/" ? "" : rawBase.replace(/\/$/, "");

const nextConfig: NextConfig = {
  ...(basePath ? { basePath } : {}),
  reactStrictMode: true,
  poweredByHeader: false,
  trailingSlash: true,
  async redirects() {
    return [
      { source: "/data", destination: "/#sheet", permanent: false },
      { source: "/studies", destination: "/#studies", permanent: false },
      { source: "/studies/:slug", destination: "/#studies", permanent: false },
      { source: "/chat", destination: "/#chat", permanent: false },
      { source: "/sources", destination: "/#sources", permanent: false },
    ];
  },
};

export default nextConfig;
