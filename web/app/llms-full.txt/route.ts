import { readDocs, readOpenApi, readTutorials, tutorialMarkdown } from "@/lib/content";
import { descricaoOperadora } from "@/lib/operadoras";
import { fontePainel, readOperadoras, readSerie } from "@/lib/operadoras-dados";
import { site } from "@/lib/site";

export const dynamic = "force-static";

export function GET() {
  const documentation = readDocs()
    .map((doc) => `# ${doc.title}\n\n${doc.content}`)
    .join("\n\n---\n\n");
  const tutorials = readTutorials()
    .map((tutorial) => `# ${tutorial.title}\n\n${tutorialMarkdown(tutorial)}`)
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
  const body = `# voa-tiss: documentação completa\n\n${documentation}\n\n${tutorials}\n\n## Operações HTTP\n\n${operations}\n\n## Operadoras\n\nFonte: ${fonte.titulo} (${fonte.licenca}), ${fonte.url}\n\n${operators}\n`;
  return new Response(body, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
