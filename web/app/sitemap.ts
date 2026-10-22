import type { MetadataRoute } from "next";
import { readOperadoras } from "@/lib/operadoras-dados";
import { moduleLinks } from "@/lib/modules";
import { indexingEnabled, site } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  if (!indexingEnabled()) return [];

  const paths = [
    "",
    "/playground",
    "/operadoras",
    ...moduleLinks.map(({ href }) => href),
    "/termos",
    ...readOperadoras().map((operadora) => `/operadoras/${operadora.registro_ans}`),
  ];
  return paths.map((route) => ({ url: new URL(route, site.url).toString() }));
}
