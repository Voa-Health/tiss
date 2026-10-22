import type { MetadataRoute } from "next";
import { readDocs, readTutorials } from "@/lib/content";
import { readOperadoras } from "@/lib/operadoras-dados";
import { indexingEnabled, site } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  if (!indexingEnabled()) return [];

  const paths = [
    "",
    "/docs",
    "/tutoriais",
    "/api",
    "/playground",
    "/operadoras",
    ...site.modules.map(({ href }) => href),
    "/termos",
    ...readDocs().map((doc) => `/docs/${doc.slug}`),
    ...readTutorials().map((tutorial) => `/tutoriais/${tutorial.slug}`),
    ...readOperadoras().map((operadora) => `/operadoras/${operadora.registro_ans}`),
  ];
  return paths.map((route) => ({ url: new URL(route, site.url).toString() }));
}
