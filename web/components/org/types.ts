import type { OrgDemoState } from "@/lib/org-mock";

export const orgSections = [
  { key: "visao", label: "Visão geral", mobileLabel: "Visão" },
  { key: "chaves", label: "Chaves", mobileLabel: "Chaves" },
  { key: "uso", label: "Uso", mobileLabel: "Uso" },
  { key: "membros", label: "Membros", mobileLabel: "Equipe" },
  { key: "tiss", label: "Configurações TISS", mobileLabel: "TISS" },
] as const;

export type OrgSection = (typeof orgSections)[number]["key"];
export type OrgRole = "admin" | "membro";

export function isOrgSection(value?: string): value is OrgSection {
  return orgSections.some((section) => section.key === value);
}

export function orgHref(
  section: OrgSection,
  role: OrgRole,
  state: OrgDemoState,
): string {
  const params = new URLSearchParams({ secao: section });
  if (role === "membro") params.set("papel", role);
  if (state !== "normal") params.set("estado", state);
  return `/org?${params.toString()}`;
}
