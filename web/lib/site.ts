const docsUrl = "https://docs.voa.health/integracao/tiss";
const tutorialsUrl = `${docsUrl}/tutoriais`;

export const site = {
  name: "tiss",
  url: "https://tiss-api.voa.health",
  github: "https://github.com/Voa-Health/tiss",
  docsUrl,
  healthplanContactUrl: "https://github.com/Voa-Health/tiss/issues/new?template=regra-de-operadora.yml",
  pypi: "https://pypi.org/project/tiss/",
  installCommand: "pip install tiss",
  mcpCommand: "claude mcp add --transport http tiss https://tiss-api.voa.health/mcp",
  mcpLocalCommand: 'claude mcp add tiss -- uvx --from "tiss[mcp]" tiss mcp',
  actionSnippet: "- uses: Voa-Health/tiss@v0\n  with:\n    paths: lotes/",
  navigation: [
    { href: docsUrl, label: "Documentação" },
    { href: tutorialUrl(), label: "Tutoriais" },
    { href: docsPageUrl("api"), label: "API" },
    { href: "/playground", label: "Playground" },
    { href: "/operadoras", label: "Operadoras" },
  ],
} as const;

export function tutorialUrl(slug?: string): string {
  return slug ? `${tutorialsUrl}/${slug}` : tutorialsUrl;
}

export function docsPageUrl(slug?: string): string {
  switch (slug) {
    case "api":
      return `${docsUrl}/api`;
    case "regras-operadora":
      return `${docsUrl}/regras-operadora`;
    case "codigos":
      return `${site.github}/blob/main/docs/codigos.md`;
    default:
      return docsUrl;
  }
}

export const siteContentWidth = 1120;
export const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";

export function keyLevelLabel(level: "login" | "verified"): string {
  return level === "verified" ? "CNPJ verificado" : "Login Voa";
}

export function formatDateTimeShort(unixTimestamp: number): string {
  return new Date(unixTimestamp * 1000).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("pt-BR", { timeZone: "UTC" });
}

export function loginSimulationEnabled(): boolean {
  return process.env.NEXT_PUBLIC_LOGIN_SIMULADO === "1";
}

export function indexingEnabled(): boolean {
  return process.env.VERCEL_ENV === "production" && process.env.NEXT_PUBLIC_INDEXAR !== "0";
}

export function robotsPolicy() {
  return indexingEnabled()
    ? { index: true, follow: true }
    : { index: false, follow: false };
}
