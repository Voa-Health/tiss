export type ModuleSlug = "recurso" | "extrator" | "cloud";
export type LaunchPrice = { amount: number | null; unit: string; note?: string };

export const launchPrices: Record<ModuleSlug, LaunchPrice> = {
  recurso: { amount: 4.9, unit: "por recurso enviado" },
  extrator: { amount: 0.39, unit: "por documento extraído" },
  cloud: {
    amount: 0.15,
    unit: "por guia acompanhada",
    note: "1.000 guias por mês grátis. Enterprise (híbrido ou self-hosted, SSO e SLA) sob consulta.",
  },
};

export const launchPriceLabel = "Preço de lançamento previsto";
export const pendingPriceLabel = "Preço de lançamento em definição";

export function formatLaunchPrice(price: LaunchPrice): string {
  if (price.amount === null) return pendingPriceLabel;
  return `${new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(price.amount)} ${price.unit}`;
}

export const monthlyVolumes = [
  { value: "ate_500", label: "Até 500 guias" },
  { value: "500_a_2000", label: "500 a 2.000 guias" },
  { value: "2000_a_10000", label: "2.000 a 10.000 guias" },
  { value: "10000_a_50000", label: "10.000 a 50.000 guias" },
  { value: "acima_50000", label: "Acima de 50.000 guias" },
] as const;

export const documentTypes = [
  { value: "guia_pdf", label: "Guia em PDF" },
  { value: "guia_foto", label: "Guia em foto" },
  { value: "demonstrativo_pdf", label: "Demonstrativo em PDF" },
  { value: "demonstrativo_planilha", label: "Demonstrativo em planilha" },
] as const;

export const hostingText =
  "Roda em Cloud no lançamento. No plano Enterprise, roda em modo híbrido ou self-hosted, e o dado clínico fica na infraestrutura do cliente.";

export const moduleContent: Record<
  ModuleSlug,
  { title: string; description: string; points: string[]; status: string }
> = {
  recurso: {
    title: "Recurso de glosa com evidência clínica",
    description:
      "Lê o demonstrativo e classifica cada glosa; busca no prontuário a evidência que sustenta o atendimento; gera o recurso no padrão TISS, validado antes do envio.",
    points: [
      "Você revisa e aprova cada recurso.",
      "Cobrado por recurso enviado.",
      "Compare cenários na calculadora de economia mensal.",
    ],
    status: "O módulo está em desenvolvimento. A lista avisa quando ele for lançado.",
  },
  extrator: {
    title: "Extrator de documentos TISS",
    description: "PDF, foto ou planilha → JSON TISS, com validação automática.",
    points: [
      "Campos sem evidência no documento ficam marcados como needs, sem valores inventados.",
      "JSON pronto para o seu sistema.",
    ],
    status: "O módulo está em desenvolvimento. A lista avisa quando ele for lançado.",
  },
  cloud: {
    title: "Voa TISS Cloud",
    description: "Acompanhe lotes, demonstrativos e regras das operadoras.",
    points: [
      "Histórico de lotes e demonstrativos.",
      "Glosas por operadora e por motivo.",
      "Alertas de lote rejeitado, prazo de recurso e regra nova da operadora.",
      "A variável VOA_TISS_API_KEY vai conectar a biblioteca ao Cloud quando ele estiver disponível.",
    ],
    status: "O módulo está em desenvolvimento. A lista avisa quando ele for lançado.",
  },
};
