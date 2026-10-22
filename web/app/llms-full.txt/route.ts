import { readDocs, readOpenApi, readTutorials, tutorialMarkdown } from "@/lib/content";
import { descricaoOperadora } from "@/lib/operadoras";
import { fontePainel, readOperadoras, readSerie } from "@/lib/operadoras-dados";
import { site } from "@/lib/site";
import { formatLaunchPrice, launchPrices, moduleContent, type ModuleSlug } from "@/lib/modules";
import { agentGuidance } from "@/lib/agent-guidance";

export const dynamic = "force-static";

export function GET() {
  const docs = readDocs();
  const documentationIndex = docs
    .map((doc) => `- [${doc.title}](${site.url}/docs/${doc.slug})`)
    .join("\n");
  const documentation = docs
    .map((doc) => `# [${doc.title}](${site.url}/docs/${doc.slug})\n\n${doc.content}`)
    .join("\n\n---\n\n");
  const tutorialData = readTutorials();
  const tutorialIndex = tutorialData
    .map((tutorial) => `- [${tutorial.title}](${site.url}/tutoriais/${tutorial.slug})`)
    .join("\n");
  const tutorials = tutorialData
    .map((tutorial) => `# [${tutorial.title}](${site.url}/tutoriais/${tutorial.slug})\n\n${tutorialMarkdown(tutorial)}`)
    .join("\n\n---\n\n");
  const operations = Object.entries(readOpenApi().paths)
    .flatMap(([path, methods]) =>
      Object.entries(methods)
        .filter(([method]) => ["get", "post", "put", "patch", "delete"].includes(method))
        .map(([method, operation]) => `${method.toUpperCase()} ${path}: ${operation.summary ?? ""}`),
    )
    .join("\n");
  const operators = readOperadoras()
    .map((operadora) => `- ${descricaoOperadora(operadora, readSerie(operadora.registro_ans))} ${site.url}/operadoras/${operadora.registro_ans}`)
    .join("\n");
  const fonte = fontePainel();
  const modules = [
    ...(["recurso", "extrator", "cloud"] as ModuleSlug[]).map((slug) => {
      const content = moduleContent[slug];
      return `### [${content.title}](${site.url}/${slug})\n\n${content.description}\n\n${content.points.join("\n")}\n\n${formatLaunchPrice(launchPrices[slug])}`;
    }),
    `### [Calculadora](${site.url}/calculadora)\n\nEstime o custo mensal dos recursos de glosa.`,
  ].join("\n\n");
  const body = [
    "# voa-tiss: documentação completa",
    "",
    "> Para operadoras, prestadores, profissionais de saúde, pacientes e gestores do SUS e do governo que usam TISS e dados abertos da ANS sobre operadoras, glosas e rede hospitalar.",
    "",
    "## Documentação",
    documentationIndex,
    "",
    documentation,
    "",
    "## Tutoriais",
    tutorialIndex,
    "",
    tutorials,
    "",
    "## Módulos",
    modules,
    "",
    "## API, OpenAPI e MCP",
    `- [Referência HTTP](${site.url}/api)`,
    `- [OpenAPI](${site.url}/openapi.json)`,
    `- [MCP](${site.url}/mcp)`,
    operations,
    "",
    "## Operadoras",
    `Fonte: ${fonte.titulo} (${fonte.licenca}), ${fonte.url}`,
    operators,
    "",
    agentGuidance,
    "",
  ].join("\n");
  return new Response(body, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
