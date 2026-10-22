import fs from "node:fs";
import path from "node:path";

export function repositoryPath(...parts: string[]): string {
  return path.join(process.cwd(), "..", ...parts);
}

export function readDocs(): { slug: string; title: string; content: string }[] {
  const directory = repositoryPath("docs");
  return fs
    .readdirSync(directory)
    .filter((file) => file.endsWith(".md"))
    .sort()
    .map((file) => {
      const content = fs.readFileSync(path.join(directory, file), "utf8");
      const title = content.match(/^# (.+)$/m)?.[1] ?? file.replace(/\.md$/, "");
      return { slug: file.replace(/\.md$/, ""), title, content };
    });
}

export function readTutorials(): Tutorial[] {
  const directory = repositoryPath("docs", "tutoriais");
  return fs
    .readdirSync(directory)
    .filter((file) => file.endsWith(".ipynb"))
    .sort()
    .map((file) => {
      const notebook = JSON.parse(fs.readFileSync(path.join(directory, file), "utf8"));
      const cells: TutorialCell[] = notebook.cells.map((cell: NotebookCell) => ({
        type: cell.cell_type,
        source: sourceText(cell.source),
        outputs: (cell.outputs ?? []).map(outputText).filter(Boolean),
      }));
      const title =
        cells
          .filter((cell) => cell.type === "markdown")
          .flatMap((cell) => cell.source.split("\n"))
          .find((line) => line.startsWith("# "))
          ?.slice(2) ?? file.replace(/\.ipynb$/, "");
      return { slug: file.replace(/\.ipynb$/, ""), title, cells };
    });
}

export function readTutorial(slug: string): Tutorial | undefined {
  return readTutorials().find((tutorial) => tutorial.slug === slug);
}

export function readOpenApi(): OpenApiDocument {
  return JSON.parse(fs.readFileSync(repositoryPath("schemas", "openapi.json"), "utf8"));
}

export function tutorialMarkdown(tutorial: Tutorial): string {
  return tutorial.cells
    .map((cell) => {
      if (cell.type === "markdown") return cell.source;
      const code = `\`\`\`python\n${cell.source}\n\`\`\``;
      return [code, ...cell.outputs.map((output) => `\`\`\`output\n${output}\n\`\`\``)].join("\n\n");
    })
    .join("\n\n");
}

function sourceText(source: string | string[]): string {
  return Array.isArray(source) ? source.join("") : source;
}

function outputText(output: NotebookOutput): string {
  if (output.output_type === "stream") return sourceText(output.text ?? "");
  const plain = output.data?.["text/plain"];
  return typeof plain === "string" || Array.isArray(plain) ? sourceText(plain) : "";
}

type NotebookCell = {
  cell_type: string;
  source: string | string[];
  outputs?: NotebookOutput[];
};

type NotebookOutput = {
  output_type: string;
  text?: string | string[];
  data?: Record<string, string | string[]>;
};

export type TutorialCell = { type: string; source: string; outputs: string[] };
export type Tutorial = { slug: string; title: string; cells: TutorialCell[] };

export type OpenApiDocument = {
  info: { title: string; description?: string };
  paths: Record<string, Record<string, OpenApiOperation>>;
};

export type OpenApiOperation = {
  operationId?: string;
  summary?: string;
  description?: string;
  tags?: string[];
  requestBody?: {
    content?: Record<string, { schema?: OpenApiSchema }>;
  };
  responses?: Record<string, { description?: string }>;
};

export type OpenApiSchema = {
  type?: string | string[];
  enum?: unknown[];
  required?: string[];
  properties?: Record<string, OpenApiSchema>;
  items?: OpenApiSchema;
};
