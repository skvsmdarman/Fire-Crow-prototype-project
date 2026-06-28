import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    unoptimized: true,
  },
  turbopack: {
    resolveAlias: {
      "react-server-dom-turbopack": "react-server-dom-webpack",
    },
  },
};

export default nextConfig;
