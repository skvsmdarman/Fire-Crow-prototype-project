import type { NextConfig } from "next";
import path from "path";

const staticExport = process.env.NEXT_STATIC_EXPORT === "true";

const nextConfig: NextConfig = {
  ...(staticExport ? { output: "export", trailingSlash: true } : {}),
  images: {
    unoptimized: true,
  },
  turbopack: {
    root: path.resolve(__dirname),
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  experimental: {
    cpus: 1,
    webpackMemoryOptimizations: true,
  },
};

export default nextConfig;
