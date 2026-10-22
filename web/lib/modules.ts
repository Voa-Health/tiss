export type ModuleSlug = "recurso" | "extrator" | "cloud" | "analise_contas" | "autorizacao";
export type LaunchPrice = { amount: number | null; unit: string; note?: string };

export const launchPrices: Record<ModuleSlug, LaunchPrice> = {
  recurso: { amount: 6.9, unit: "por recurso enviado" },
  extrator: { amount: 0.49, unit: "por documento extraído" },
  cloud: {
    amount: 0.05,
    unit: "por guia acompanhada",
    note: "1.000 guias por mês grátis. Enterprise (híbrido ou self-hosted, SSO e SLA) sob consulta.",
  },
  analise_contas: {
    amount: 0.49,
    unit: "por guia analisada",
    note: "Enterprise (híbrido ou self-hosted, SSO e SLA) sob consulta.",
  },
  autorizacao: {
    amount: 1.9,
    unit: "por solicitação analisada",
    note: "Enterprise (híbrido ou self-hosted, SSO e SLA) sob consulta.",
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
  { value: "ate_500", label: "Até 500" },
  { value: "500_a_2000", label: "500 a 2.000" },
  { value: "2000_a_10000", label: "2.000 a 10.000" },
  { value: "10000_a_50000", label: "10.000 a 50.000" },
  { value: "acima_50000", label: "Acima de 50.000" },
] as const;

export const documentTypes = [
  { value: "guia_pdf", label: "Guia em PDF" },
  { value: "guia_foto", label: "Guia em foto" },
  { value: "demonstrativo_pdf", label: "Demonstrativo em PDF" },
  { value: "demonstrativo_planilha", label: "Demonstrativo em planilha" },
] as const;

export const hostingText =
  "Roda em Cloud no lançamento. No plano Enterprise, roda em modo híbrido ou self-hosted, e o dado clínico fica na infraestrutura do cliente.";

export type ModuleContent = {
  href: string;
  label: string;
  title: string;
  description: string;
  points: string[];
  volumeLabel: string;
  status: string;
};

const status = "O módulo está em desenvolvimento. A lista avisa quando ele for lançado.";

export const moduleContent: Record<ModuleSlug, ModuleContent> = {
  recurso: {
    href: "/recurso",
    label: "Recurso de glosa",
    title: "Recurso de glosa com evidência clínica",
    description:
      "Lê o demonstrativo e classifica cada glosa; busca no prontuário a evidência que sustenta o atendimento; gera o recurso no padrão TISS, validado antes do envio.",
    points: [
      "Você revisa e aprova cada recurso.",
      "Cobrado por recurso enviado.",
      "Compare cenários na calculadora de economia mensal.",
    ],
    volumeLabel: "Volume mensal de guias",
    status,
  },
  extrator: {
    href: "/extrator",
    label: "Extrator",
    title: "Extrator de documentos TISS",
    description: "PDF, foto ou planilha → JSON TISS, com validação automática.",
    points: [
      "Campos sem evidência no documento ficam marcados como needs, sem valores inventados.",
      "JSON pronto para o seu sistema.",
    ],
    volumeLabel: "Volume mensal de guias",
    status,
  },
  cloud: {
    href: "/cloud",
    label: "Cloud",
    title: "Voa TISS Cloud",
    description: "Acompanhe lotes, demonstrativos e regras das operadoras.",
    points: [
      "Histórico de lotes e demonstrativos.",
      "Glosas por operadora e por motivo.",
      "Alertas de lote rejeitado, prazo de recurso e regra nova da operadora.",
      "A variável VOA_TISS_API_KEY vai conectar a biblioteca ao Cloud quando ele estiver disponível.",
    ],
    volumeLabel: "Volume mensal de guias",
    status,
  },
  analise_contas: {
    href: "/analise-contas",
    label: "Análise de contas",
    title: "Análise de contas com agente",
    description:
      "Um agente pré-analisa 100% das contas recebidas: regras da operadora, duplicidade, compatibilidade entre procedimento, CID, sexo e idade, pacote e OPME, e divergência com a autorização. Só o que tem divergência vai ao auditor.",
    points: [
      "O agente propõe e o auditor decide a glosa, sempre com a regra ou a evidência citada.",
      "Por guia, o agente indica liberar, glosa proposta (código da Tabela 38, regra ou evidência e valor) ou auditor, com a divergência descrita.",
      "Nenhuma glosa é final sem aceite humano.",
      "O que é determinístico roda na biblioteca aberta: check, audit, autorização e Tabela 38.",
      "Preço fixo por guia analisada, nunca percentual da glosa.",
    ],
    volumeLabel: "Volume mensal de guias recebidas",
    status,
  },
  autorizacao: {
    href: "/autorizacao",
    label: "Autorização prévia",
    title: "Autorização prévia com agente",
    description:
      "Um agente analisa as solicitações de autorização SP/SADT, aprova as que cumprem a regra e encaminha as demais ao auditor com o parecer e a justificativa rascunhados, para responder no prazo da RN 623/2024.",
    points: [
      "A aprovação automática acontece só por regra da operadora.",
      "A negativa é sempre de um profissional da operadora, com o motivo por escrito e claro, como exige a RN 623/2024. O agente rascunha o texto e nunca nega sozinho.",
      "Quando falta dado, o agente lista exatamente o que pedir ao prestador.",
      "Toda decisão fica rastreável, com a regra ou a fonte citada.",
      "A resposta sai em XML TISS válido.",
      "Preço fixo por solicitação analisada.",
    ],
    volumeLabel: "Volume mensal de solicitações de autorização",
    status,
  },
};

export type ModuleLink = { href: string; label: string; description: string };

const groups: { title: string; slugs: ModuleSlug[]; extra: ModuleLink[] }[] = [
  {
    title: "Para prestadores",
    slugs: ["recurso", "extrator", "cloud"],
    extra: [
      {
        href: "/calculadora",
        label: "Calculadora",
        description: "Estime o custo mensal de recursos de glosa.",
      },
    ],
  },
  { title: "Para operadoras", slugs: ["analise_contas", "autorizacao"], extra: [] },
];

export const moduleGroups: { title: string; slugs: ModuleSlug[]; links: ModuleLink[] }[] =
  groups.map(({ title, slugs, extra }) => ({
    title,
    slugs,
    links: [
      ...slugs.map((slug) => ({
        href: moduleContent[slug].href,
        label: moduleContent[slug].label,
        description: moduleContent[slug].description,
      })),
      ...extra,
    ],
  }));

export const moduleLinks: ModuleLink[] = moduleGroups.flatMap(({ links }) => links);
