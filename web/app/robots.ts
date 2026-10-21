import type { MetadataRoute } from "next";
import { robotsPolicy, site } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  const policy = robotsPolicy();
  return {
    rules: { userAgent: "*", allow: policy.index ? "/" : undefined, disallow: policy.index ? undefined : "/" },
    sitemap: `${site.url}/sitemap.xml`,
    host: site.url,
  };
}
