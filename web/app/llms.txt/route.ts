import { readDocs, readOpenApi, readTutorials } from "@/lib/content";
import { readOperadoras } from "@/lib/operadoras-dados";
import { operationAnchor, site } from "@/lib/site";
import { moduleContent } from "@/lib/modules";

export const dynamic = "force-static";

export function GET() {
  const docs = readDocs()
    .map((doc) => `- [${doc.title}](${site.url}/docs/${doc.slug})`)
    .join("\n");
  const tutorials = readTutorials()
    .map((tutorial) => `- [${tutorial.title}](${site.url}/tutoriais/${tutorial.slug})`)
    .join("\n");
  const operations = Object.entries(readOpenApi().paths)
    .flatMap(([path, methods]) =>
      Object.keys(methods)
        .filter((method) => ["get", "post", "put", "patch", "delete"].includes(method))
        .map((method) => `- \`${method.toUpperCase()} ${path}\` — ${site.url}/api#${operationAnchor(method, path)}`),
    )
    .join("\n");
  const operators = readOperadoras()
    .map((operadora) => `- [${operadora.razao_social} (${operadora.registro_ans})](${site.url}/operadoras/${operadora.registro_ans})`)
    .join("\n");
  const moduleDescriptions: Record<string, string> = {
    recurso: moduleContent.recurso.description,
    extrator: moduleContent.extrator.description,
    cloud: moduleContent.cloud.description,
    calculadora: "Estime o custo mensal de recursos de glosa.",
  };
  const modules = site.modules
    .map(({ href, label, slug }) => `- [${label}](${site.url}${href}) — ${moduleDescriptions[slug]}`)
    .join("\n");
  const body = [
    "# voa-tiss",
    "",
    "> Documentação técnica para validar lotes TISS antes do envio à operadora.",
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
    "## API",
    `- [Referência HTTP](${site.url}/api)`,
    `- [OpenAPI](${site.url}/openapi.json)`,
    `- [MCP](${site.url}/mcp)`,
    operations,
    "",
    "## Operadoras",
    operators,
    "",
  ].join("\n");
  return new Response(body, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
