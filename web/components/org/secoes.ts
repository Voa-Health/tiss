import type { EstadoDaOrg } from "@/lib/org/tipos";

export const secoesDaOrg = [
  { key: "visao", label: "Visão geral" },
  { key: "chaves", label: "Chaves" },
  { key: "uso", label: "Uso" },
  { key: "cobranca", label: "Cobrança" },
  { key: "membros", label: "Membros" },
  { key: "tiss", label: "Configurações TISS" },
  { key: "regras", label: "Regras" },
  { key: "auditoria", label: "Auditoria" },
  { key: "contas", label: "Contas" },
  { key: "mapa", label: "Mapa de rejeição" },
] as const;

export type SecaoDaOrg = (typeof secoesDaOrg)[number]["key"];

type OrgDaNavegacao = Pick<EstadoDaOrg, "type" | "is_admin" | "my_areas" | "rejection_map">;

export function secoesVisiveisDaOrg(org?: OrgDaNavegacao) {
  if (!org) return secoesDaOrg;
  const deOperadora = org.type === "pay";
  const podeVerRegras = deOperadora && (
    org.is_admin || org.my_areas.includes("auditoria") || org.my_areas.includes("administration")
  );
  return secoesDaOrg.filter((secao) => {
    if (secao.key === "mapa") return podeVerRegras && org.rejection_map?.eligible === true;
    if (secao.key === "regras" || secao.key === "auditoria") return podeVerRegras;
    if (secao.key === "contas") return deOperadora;
    return true;
  });
}

export function secaoValida(valor?: string, org?: OrgDaNavegacao): SecaoDaOrg {
  return secoesVisiveisDaOrg(org).find((secao) => secao.key === valor)?.key ?? "visao";
}

export function hrefDaOrg(secao: SecaoDaOrg, painel = false): string {
  if (secao === "cobranca") return `/org/cobranca${painel ? "?painel=assistente" : ""}`;
  const params = new URLSearchParams({ secao });
  if (painel) params.set("painel", "assistente");
  return `/org?${params.toString()}`;
}

export const ROTULO_DO_TIPO: Record<string, string> = {
  prov: "Prestador",
  pay: "Operadora",
  bus: "Empresa",
  govt: "Governo",
  other: "Outro",
};

export type PacoteDeRegras = { registro: string; razaoSocial: string; regras: number };
