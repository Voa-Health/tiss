export const secoesDaOrg = [
  { key: "visao", label: "Visão geral", descricao: "Dados da organização, termos e atalhos do seu tipo." },
  { key: "chaves", label: "Chaves", descricao: "Chaves de acesso à API e ao MCP hospedados." },
  { key: "uso", label: "Uso", descricao: "Chamadas dos últimos 30 dias e custo estimado." },
  { key: "membros", label: "Membros", descricao: "Quem faz parte da organização e de que Áreas cuida." },
  { key: "tiss", label: "Configurações TISS", descricao: "Registro ANS, padrão e limite de guias por lote." },
] as const;

export type SecaoDaOrg = (typeof secoesDaOrg)[number]["key"];

export function secaoValida(valor?: string): SecaoDaOrg {
  return secoesDaOrg.find((secao) => secao.key === valor)?.key ?? "visao";
}

export function hrefDaOrg(secao: SecaoDaOrg, painel = false): string {
  const params = new URLSearchParams({ secao });
  if (painel) params.set("painel", "assistente");
  return `/org?${params.toString()}`;
}

export const ROTULO_DO_TIPO: Record<string, string> = {
  prov: "Prestador",
  pay: "Operadora",
  bus: "Empresa",
  govt: "Governo",
};

export type PacoteDeRegras = { registro: string; razaoSocial: string; regras: number };
