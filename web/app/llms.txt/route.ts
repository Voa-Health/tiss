import { readDocs, readOpenApi, readTutorials } from "@/lib/content";
import { readOperadoras } from "@/lib/operadoras-dados";
import { docsPageUrl, operationAnchor, site, tutorialUrl } from "@/lib/site";
import { moduleGroups } from "@/lib/modules";
import { agentGuidance } from "@/lib/agent-guidance";

export const dynamic = "force-static";

export function GET() {
  const docs = readDocs()
    .map((doc) => `- [${doc.title}](${docsPageUrl(doc.slug)})`)
    .join("\n");
  const tutorials = readTutorials()
    .map((tutorial) => `- [${tutorial.title}](${tutorialUrl(tutorial.slug)})`)
    .join("\n");
  const operations = Object.entries(readOpenApi().paths)
    .flatMap(([path, methods]) =>
      Object.keys(methods)
        .filter((method) => ["get", "post", "put", "patch", "delete"].includes(method))
        .map((method) => `- \`${method.toUpperCase()} ${path}\` — ${site.url}/api#${operationAnchor(method, path)}`),
    )
    .join("\n");
  const healthplans = readOperadoras()
    .map((operadora) => `- [${operadora.razao_social} (${operadora.registro_ans})](${site.url}/operadoras/${operadora.registro_ans})`)
    .join("\n");
  const modules = moduleGroups
    .map(({ title, links }) =>
      [
        `### ${title}`,
        ...links.map(({ href, label, description }) => `- [${label}](${site.url}${href}) — ${description}`),
      ].join("\n"),
    )
    .join("\n\n");
  const body = [
    "# voa-tiss",
    "",
    "> Documentação técnica para operadoras, prestadores, profissionais de saúde, pacientes e gestores do SUS e do governo que usam TISS e dados abertos da ANS sobre operadoras, glosas e rede hospitalar.",
    "",
    "## Documentação",
    docs,
    "",
    "## Tutoriais",
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
    healthplans,
    "",
    agentGuidance,
    "",
  ].join("\n");
  return new Response(body, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
