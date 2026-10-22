import { type ModuleSlug } from "@/lib/modules";
import { operationAnchor, site } from "@/lib/site";

export type AudienceItem = { label: string; description: string; href: string; linkLabel: string };
export type Audience = {
  id: string;
  title: string;
  summary: string;
  items: AudienceItem[];
  modules: ModuleSlug[];
  cta: { href: string; label: string };
};

const demonstrativo = "/tutoriais/02-demonstrativo-e-conciliacao";
const sandbox = "/tutoriais/06-operadora-simulada";

export const healthplanModules: ModuleSlug[] = ["analise_contas", "autorizacao"];

export const healthplanFeatures: AudienceItem[] = [
  {
    label: "Checagem com as suas regras",
    description:
      "Rode check com o seu pacote de regras na porta de recebimento, offline, na sua infraestrutura e sem enviar dado à Voa.",
    href: `${site.docsUrl}/regras-operadora`,
    linkLabel: "Ver regras por operadora",
  },
  {
    label: "Mapa de rejeição por prestador",
    description:
      "Veja quais prestadores e quais regras geram mais retrabalho nos lotes recebidos, agregado por prestador e código.",
    href: site.docsUrl,
    linkLabel: "Ver documentação",
  },
  {
    label: "Sandbox com as suas regras",
    description:
      "O prestador envia o lote à operadora simulada com o seu pacote e recebe o demonstrativo que receberia de você.",
    href: sandbox,
    linkLabel: "Ver tutorial",
  },
  {
    label: "Autorização TISS aberta",
    description:
      "Monte, leia e valide solicitação e resposta de autorização SP/SADT, com checagem determinística contra as suas regras.",
    href: site.docsUrl,
    linkLabel: "Ver documentação",
  },
  {
    label: "Regras publicadas com selo Oficial",
    description:
      "Publique o pacote de regras como dado aberto para que os prestadores validem com ele antes do envio.",
    href: "/operadoras#publicar-regras",
    linkLabel: "Como publicar",
  },
];

export const audiences: Audience[] = [
  {
    id: "operadora",
    title: "Operadora",
    summary: "Adote sem contrato: tudo roda na sua infraestrutura e nenhum dado vai para a Voa.",
    items: healthplanFeatures,
    modules: healthplanModules,
    cta: { href: "/operadoras", label: "Ver para operadoras" },
  },
  {
    id: "prestador",
    title: "Prestador e profissional de saúde",
    summary: "Pegue o erro antes da operadora e entenda por que uma guia foi glosada.",
    items: [
      {
        label: "Validar, corrigir e revalidar",
        description: "Valide o lote com XSD e regras de negócio e aplique correções determinísticas.",
        href: "/tutoriais/01-validar-um-lote",
        linkLabel: "Ver tutorial",
      },
      {
        label: "Operadora simulada",
        description: "Envie o lote e receba o demonstrativo antes do envio real.",
        href: sandbox,
        linkLabel: "Ver tutorial",
      },
      {
        label: "TUSS e SP/SADT",
        description: "Confira códigos TUSS e gere a guia SP/SADT sem decorar o manual.",
        href: "/tutoriais/03-tuss-e-sp-sadt",
        linkLabel: "Ver tutorial",
      },
    ],
    modules: ["recurso", "extrator", "cloud"],
    cta: { href: "/playground", label: "Experimentar playground" },
  },
  {
    id: "paciente",
    title: "Paciente",
    summary: "Entenda o que a operadora decidiu sobre o seu atendimento.",
    items: [
      {
        label: "Entender uma glosa",
        description: "glosa_explain explica em linguagem simples cada código da Tabela 38 da ANS.",
        href: `/api#${operationAnchor("get", "/v1/glosas/{codigo}")}`,
        linkLabel: "Ver glosa_explain",
      },
      {
        label: "Ler o demonstrativo",
        description: "Veja o que foi pago e o que foi glosado em cada guia.",
        href: demonstrativo,
        linkLabel: "Ver tutorial",
      },
      {
        label: "Achar a rede do plano",
        description: "Busque os hospitais da rede de cada operadora.",
        href: "/operadoras",
        linkLabel: "Buscar na rede",
      },
    ],
    modules: [],
    cta: { href: "/operadoras", label: "Buscar operadora" },
  },
  {
    id: "sus-governo",
    title: "SUS e governo",
    summary: "Consulte dados abertos da ANS (CC BY) sobre a saúde suplementar.",
    items: [
      {
        label: "Perfil das operadoras",
        description: "Cadastro e indicadores públicos de cada operadora ativa na ANS.",
        href: "/operadoras",
        linkLabel: "Ver operadoras",
      },
      {
        label: "Glosas por operadora",
        description: "Indicadores do Painel de Glosas da ANS, por operadora e período.",
        href: "/operadoras",
        linkLabel: "Ver indicadores",
      },
      {
        label: "Rede hospitalar",
        description: "Estabelecimentos da rede de cada operadora, por município.",
        href: "/operadoras",
        linkLabel: "Buscar na rede",
      },
    ],
    modules: [],
    cta: { href: "/operadoras", label: "Ver dados abertos" },
  },
];
