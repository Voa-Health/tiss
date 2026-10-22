export const site = {
  name: "voa-tiss",
  url: "https://tiss-api.voa.health",
  github: "https://github.com/Voa-Health/tiss",
  healthplanContactUrl: "https://github.com/Voa-Health/tiss/issues/new?template=regra-de-operadora.yml",
  pypi: "https://pypi.org/project/voa-tiss/",
  installCommand: "pip install voa-tiss",
  mcpCommand: "claude mcp add --transport http voa-tiss https://tiss-api.voa.health/mcp",
  navigation: [
    { href: "/docs", label: "Documentação" },
    { href: "/tutoriais", label: "Tutoriais" },
    { href: "/api", label: "API" },
    { href: "/playground", label: "Playground" },
    { href: "/operadoras", label: "Operadoras" },
  ],
} as const;

export const siteContentWidth = 1120;
export const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";

export type KeyCredentials = {
  chave: string;
  refresh_token: string;
  nivel: "login" | "verified";
  expira_em: number;
};

export function keyLevelLabel(level: KeyCredentials["nivel"]): string {
  return level === "verified" ? "CNPJ verificado" : "Login Voa";
}

export function formatDateTime(unixTimestamp: number): string {
  return new Date(unixTimestamp * 1000).toLocaleString("pt-BR");
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

export function operationAnchor(method: string, route: string): string {
  return `${method}-${route}`.replace(/[^a-z0-9-]+/gi, "-").toLowerCase();
}

export function loginSimulationEnabled(): boolean {
  return process.env.NEXT_PUBLIC_LOGIN_SIMULADO === "1";
}

export function createMockCredentials(): KeyCredentials {
  const suffix = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
  return {
    chave: `vt_exemplo_${suffix}`,
    refresh_token: `rt_exemplo_${suffix}`,
    nivel: "login",
    expira_em: Math.floor(Date.now() / 1000) + 24 * 60 * 60,
  };
}

export function keyFragmentUrl(credentials: KeyCredentials): string {
  return `/chaves#${new URLSearchParams({
    chave: credentials.chave,
    refresh_token: credentials.refresh_token,
    nivel: credentials.nivel,
    expira_em: String(credentials.expira_em),
  })}`;
}

export function indexingEnabled(): boolean {
  return process.env.VERCEL_ENV === "production" && process.env.NEXT_PUBLIC_INDEXAR !== "0";
}

export function robotsPolicy() {
  return indexingEnabled()
    ? { index: true, follow: true }
    : { index: false, follow: false };
}

export function loginUrl(): string {
  if (loginSimulationEnabled()) {
    return keyFragmentUrl(createMockCredentials());
  }
  return `${process.env.NEXT_PUBLIC_API_URL ?? ""}/v1/auth/login`;
}
