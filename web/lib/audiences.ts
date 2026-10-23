import { type ModuleSlug } from "@/lib/modules";
import { docsPageUrl, site, tutorialUrl } from "@/lib/site";

export type TerminalDemo = { src: string; alt: string; width: number; height: number };
export type AudienceItem = {
  label: string;
  description: string;
  href: string;
  linkLabel: string;
  demo?: TerminalDemo;
};

function terminalDemo(name: string, alt: string): TerminalDemo {
  return { src: `/demos/${name}.gif`, alt, width: 1000, height: 640 };
}
export type Audience = {
  id: string;
  title: string;
  summary: string;
  items: AudienceItem[];
  modules: ModuleSlug[];
  cta: { href: string; label: string };
};

const demonstrativo = tutorialUrl("02-demonstrativo-e-conciliacao");
const sandbox = tutorialUrl("06-operadora-simulada");

export const healthplanModules: ModuleSlug[] = ["analise_contas", "autorizacao"];

export const healthplanFeatures: AudienceItem[] = [
  {
    label: "Checagem com as suas regras",
    description:
      "Rode check com o seu pacote de regras na porta de recebimento, offline, na sua infraestrutura e sem enviar dado à Voa.",
    href: docsPageUrl("regras-operadora"),
    linkLabel: "Ver regras por operadora",
    demo: terminalDemo(
      "checagem",
      "Terminal: check com um pacote de regras da operadora aponta a carteira fora do padrão, com a regra e a fonte.",
    ),
  },
  {
    label: "Mapa de rejeição por prestador",
    description:
      "Veja quais prestadores e quais regras geram mais retrabalho nos lotes recebidos, agregado por prestador e código.",
    href: tutorialUrl("08-mapa-de-rejeicao"),
    linkLabel: "Ver tutorial",
    demo: terminalDemo(
      "mapa",
      "Terminal: rejection_map agrega os achados de dois lotes por prestador e código, com o CPF pseudonimizado como cpf:hmac.",
    ),
  },
  {
    label: "Sandbox com as suas regras",
    description:
      "O prestador envia o lote à operadora simulada com o seu pacote e recebe o demonstrativo que receberia de você.",
    href: sandbox,
    linkLabel: "Ver tutorial",
    demo: terminalDemo(
      "sandbox",
      "Terminal: enviar_lote entrega o lote à operadora simulada com as regras dela e o demonstrativo mostra a glosa citando a regra.",
    ),
  },
  {
    label: "Autorização TISS aberta",
    description:
      "Monte, leia e valide solicitação e resposta de autorização SP/SADT, com checagem determinística contra as suas regras.",
    href: site.docsUrl,
    linkLabel: "Ver documentação",
    demo: terminalDemo(
      "autorizacao",
      "Terminal: check_autorizacao com as regras da operadora simulada encaminha a solicitação ao auditor e cita a regra de autorização prévia.",
    ),
  },
  {
    label: "Regras publicadas com selo Oficial",
    description:
      "Publique o pacote de regras como dado aberto para que os prestadores validem com ele antes do envio.",
    href: "/operadoras#publicar-regras",
    linkLabel: "Como publicar",
    demo: terminalDemo(
      "oficial",
      "Terminal: validate_package aceita o pacote oficial da operadora, recusa o selo para mantenedor comunidade e check cita a regra oficial.",
    ),
  },
];

export const cliFeature: AudienceItem = {
  label: "Validar, corrigir e revalidar",
  description: "Valide o lote com XSD e regras de negócio e aplique correções determinísticas.",
  href: tutorialUrl("01-validar-um-lote"),
  linkLabel: "Ver tutorial",
  demo: terminalDemo(
    "cli",
    "Terminal: tiss validate aprova o lote e confere o hash, o código do procedimento sai do lote para tiss tuss e o código da glosa sai do demonstrativo para tiss glosa.",
  ),
};

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
      cliFeature,
      {
        label: "Operadora simulada",
        description: "Envie o lote e receba o demonstrativo antes do envio real.",
        href: sandbox,
        linkLabel: "Ver tutorial",
      },
      {
        label: "TUSS e SP/SADT",
        description: "Confira códigos TUSS e gere a guia SP/SADT sem decorar o manual.",
        href: tutorialUrl("03-tuss-e-sp-sadt"),
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
        href: docsPageUrl("api"),
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
