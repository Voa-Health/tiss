import type { NextConfig } from "next";

const localApi = process.env.TISS_API_LOCAL;
const nextConfig: NextConfig =
  process.env.NODE_ENV === "development" && localApi
    ? {
        async rewrites() {
          return [{ source: "/v1/:path*", destination: `${localApi}/v1/:path*` }];
        },
      }
    : {};

export default nextConfig;
