import { readDocs, readOpenApi, readTutorials, tutorialMarkdown } from "@/lib/content";
import { descricaoOperadora } from "@/lib/operadoras";
import { fontePainel, readOperadoras, readSerie } from "@/lib/operadoras-dados";
import { docsPageUrl, site, tutorialUrl } from "@/lib/site";
import { formatLaunchPrice, launchPrices, moduleContent, moduleGroups } from "@/lib/modules";
import { agentGuidance } from "@/lib/agent-guidance";
import { audiences } from "@/lib/audiences";

export const dynamic = "force-static";

export function GET() {
  const docs = readDocs();
  const documentationIndex = docs
    .map((doc) => `- [${doc.title}](${docsPageUrl(doc.slug)})`)
    .join("\n");
  const documentation = docs
    .map((doc) => `# [${doc.title}](${docsPageUrl(doc.slug)})\n\n${doc.content}`)
    .join("\n\n---\n\n");
  const tutorialData = readTutorials();
  const tutorialIndex = tutorialData
    .map((tutorial) => `- [${tutorial.title}](${tutorialUrl(tutorial.slug)})`)
    .join("\n");
  const tutorials = tutorialData
    .map((tutorial) => `# [${tutorial.title}](${tutorialUrl(tutorial.slug)})\n\n${tutorialMarkdown(tutorial)}`)
    .join("\n\n---\n\n");
  const operations = Object.entries(readOpenApi().paths)
    .flatMap(([path, methods]) =>
      Object.entries(methods)
        .filter(([method]) => ["get", "post", "put", "patch", "delete"].includes(method))
        .map(([method, operation]) => `${method.toUpperCase()} ${path}: ${operation.summary ?? ""}`),
    )
    .join("\n");
  const healthplans = readOperadoras()
    .map((operadora) => `- ${descricaoOperadora(operadora, readSerie(operadora.registro_ans))} ${site.url}/operadoras/${operadora.registro_ans}`)
    .join("\n");
  const fonte = fontePainel();
  const modules = moduleGroups
    .map(({ title, slugs, links }) =>
      [
        `### ${title}`,
        ...slugs.map((slug) => {
          const content = moduleContent[slug];
          return `#### [${content.title}](${site.url}${content.href})\n\n${content.description}\n\n${content.points.join("\n")}\n\n${formatLaunchPrice(launchPrices[slug])}`;
        }),
        ...links
          .slice(slugs.length)
          .map(({ href, label, description }) => `#### [${label}](${site.url}${href})\n\n${description}`),
      ].join("\n\n"),
    )
    .join("\n\n");
  const audienceSections = audiences
    .map(({ title, summary, items, modules: slugs }) =>
      [
        `### ${title}`,
        "",
        summary,
        "",
        ...items.map(
          ({ label, description, href }) =>
            `- [${label}](${new URL(href, site.url)}): ${description}`,
        ),
        ...slugs.map((slug) => `- [${moduleContent[slug].title}](${site.url}${moduleContent[slug].href}): ${formatLaunchPrice(launchPrices[slug])}`),
      ].join("\n"),
    )
    .join("\n\n");
  const body = [
    "# voa-tiss: documentação completa",
    "",
    "> Para operadoras, prestadores, profissionais de saúde, pacientes e gestores do SUS e do governo que usam TISS e dados abertos da ANS sobre operadoras, glosas e rede hospitalar.",
    "",
    "## Para quem é",
    audienceSections,
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
    `- [Referência HTTP](${docsPageUrl("api")})`,
    `- [OpenAPI](${site.url}/openapi.json)`,
    `- [MCP](${site.url}/mcp)`,
    operations,
    "",
    "## Operadoras",
    `Fonte: ${fonte.titulo} (${fonte.licenca}), ${fonte.url}`,
    healthplans,
    "",
    agentGuidance,
    "",
  ].join("\n");
  return new Response(body, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
