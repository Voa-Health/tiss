import { launchPrices, type ModuleSlug } from "@/lib/modules";
import { docsPageUrl, site, tutorialUrl } from "@/lib/site";

export type SolutionLink = { href: string; label: string; description: string; tag?: string };
export type SolutionGroup = { title: string; audience: string; links: SolutionLink[] };

const free = "Grátis";

function price(slug: ModuleSlug, unit: string): string {
  const amount = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
    launchPrices[slug].amount ?? 0,
  );
  return `${amount}/${unit}`;
}

export const solutionGroups: SolutionGroup[] = [
  {
    title: "Proteger o recebimento",
    audience: "Hospitais e clínicas",
    links: [
      {
        href: "/playground",
        label: "Pegar o erro antes da operadora",
        description: "XSD, regras da operadora e hash antes do envio.",
        tag: free,
      },
      {
        href: "/recurso",
        label: "Recorrer de glosa com fundamento",
        description: "Recurso com a regra e a fonte citadas.",
        tag: price("recurso", "recurso"),
      },
      {
        href: "/extrator",
        label: "Tirar a digitação de guias",
        description: "PDF e foto viram dados TISS.",
        tag: price("extrator", "documento"),
      },
      {
        href: "/cloud",
        label: "Acompanhar cada guia até o pagamento",
        description: "Envio, glosa e pagamento em um só lugar.",
        tag: price("cloud", "guia"),
      },
    ],
  },
  {
    title: "Reduzir desperdício e fraude",
    audience: "Operadoras",
    links: [
      {
        href: "/analise-contas",
        label: "Auditar contas com agente",
        description: "Aponta indícios com fonte; o auditor decide.",
        tag: price("analise_contas", "guia"),
      },
      {
        href: "/autorizacao",
        label: "Autorização prévia com auditor no controle",
        description: "Aprova por regra e nunca nega sozinha.",
        tag: price("autorizacao", "solicitação"),
      },
      {
        href: "/operadoras#publicar-regras",
        label: "Publicar regras de envio",
        description: "O prestador checa suas regras antes de enviar.",
        tag: free,
      },
    ],
  },
  {
    title: "Inteligência analítica",
    audience: "Prestadores e operadoras",
    links: [
      {
        href: tutorialUrl("02-demonstrativo-e-conciliacao"),
        label: "Conferir o que foi pago",
        description: "Demonstrativo conciliado guia a guia.",
        tag: free,
      },
      {
        href: tutorialUrl("08-mapa-de-rejeicao"),
        label: "Ver quais prestadores mais erram",
        description: "Rejeições por prestador, CPF pseudonimizado.",
        tag: free,
      },
      {
        href: "/operadoras#operadoras-ativas",
        label: "Comparar glosa e prazo com o mercado",
        description: "Dados abertos da ANS por operadora.",
        tag: free,
      },
    ],
  },
  {
    title: "TI e inovação",
    audience: "Integração, produto e inovação",
    links: [
      {
        href: docsPageUrl("api"),
        label: "API HTTP e MCP para o seu agente",
        description: "OpenAPI, tools MCP e prompts prontos.",
      },
      {
        href: tutorialUrl("06-operadora-simulada"),
        label: "Testar com operadora simulada",
        description: "Lotes e demonstrativos sintéticos.",
      },
      {
        href: site.github,
        label: "Código aberto, roda offline",
        description: "Biblioteca Python sem envio de dados.",
      },
    ],
  },
];
