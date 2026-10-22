import type { NextConfig } from "next";
import { docsPageUrl, site, tutorialUrl } from "./lib/site";

const localApi = process.env.TISS_API_LOCAL;
const nextConfig: NextConfig = {
  async redirects() {
    return [
      { source: "/docs", destination: site.docsUrl, permanent: true },
      { source: "/tutoriais", destination: tutorialUrl(), permanent: true },
      { source: "/tutoriais/:slug", destination: tutorialUrl(":slug"), permanent: true },
      { source: "/api", destination: docsPageUrl("api"), permanent: true },
      { source: "/docs/api", destination: docsPageUrl("api"), permanent: true },
      {
        source: "/docs/regras-operadora",
        destination: docsPageUrl("regras-operadora"),
        permanent: true,
      },
      { source: "/docs/codigos", destination: docsPageUrl("codigos"), permanent: true },
      { source: "/docs/:slug", destination: site.docsUrl, permanent: true },
    ];
  },
  ...(process.env.NODE_ENV === "development" && localApi
    ? {
        async rewrites() {
          return [{ source: "/v1/:path*", destination: `${localApi}/v1/:path*` }];
        },
      }
    : {}),
};

export default nextConfig;
