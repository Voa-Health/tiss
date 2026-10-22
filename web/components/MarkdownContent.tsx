import type { Components } from "react-markdown";
import { Children, isValidElement, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { docsPageUrl, site } from "@/lib/site";
import { CodeBlock } from "./CodeBlock";
import { MermaidBlock } from "./MermaidBlock";

function repositoryLink(href: string, sourcePath: string): string {
  if (/^(https?:|mailto:|#|\/)/.test(href)) return href;
  const [file, fragment] = href.split("#", 2);
  const parts = sourcePath.split("/").slice(0, -1);
  for (const segment of file.split("/")) {
    if (!segment || segment === ".") continue;
    if (segment === "..") parts.pop();
    else parts.push(segment);
  }
  const clean = parts.join("/");
  const suffix = fragment ? `#${fragment}` : "";
  if (/^docs\/[^/]+\.md$/.test(clean)) return `${docsPageUrl(clean.slice(5, -3))}${suffix}`;
  if (/^docs\/tutoriais\/[^/]+\.ipynb$/.test(clean)) {
    return `/tutoriais/${clean.split("/").at(-1)?.replace(/\.ipynb$/, "")}${suffix}`;
  }
  return `${site.github}/blob/main/${clean}${suffix}`;
}

function removeMatchingHeading(content: string, title?: string): string {
  if (!title) return content;
  const lines = content.split("\n");
  const firstHeading = lines.findIndex((line) => line.startsWith("# "));
  if (firstHeading < 0 || lines[firstHeading].slice(2).trim() !== title.trim()) return content;
  lines.splice(firstHeading, 1);
  return lines.join("\n");
}

export function MarkdownContent({
  content,
  sourcePath,
  title,
}: {
  content: string;
  sourcePath: string;
  title?: string;
}) {
  const components: Components = {
    pre({ children }) {
      const child = Children.toArray(children)[0];
      if (
        isValidElement(child) &&
        (child.type === MermaidBlock || child.type === CodeBlock)
      ) {
        return child;
      }
      if (isValidElement(child) && child.type === "code") {
        const props = child.props as { children?: ReactNode; className?: string };
        const language = props.className?.match(/language-([^\s]+)/)?.[1];
        return (
          <CodeBlock
            code={String(props.children ?? "").replace(/\n$/, "")}
            output={language === "output"}
          />
        );
      }
      return <pre>{children}</pre>;
    },
    a({ href = "", children, ...props }) {
      const destination = repositoryLink(href, sourcePath);
      const external = destination.startsWith("http");
      return (
        <a
          href={destination}
          target={external ? "_blank" : undefined}
          rel={external ? "noreferrer" : undefined}
          {...props}
        >
          {children}
        </a>
      );
    },
    code({ className, children, ...props }) {
      const chart = String(children).replace(/\n$/, "");
      if (className?.includes("language-mermaid")) return <MermaidBlock chart={chart} />;
      if (className?.includes("language-")) {
        return (
          <CodeBlock
            code={chart}
            output={className.includes("language-output")}
          />
        );
      }
      return <code className={className} {...props}>{children}</code>;
    },
  };
  const markdown = removeMatchingHeading(content, title);
  return (
    <article className="markdown-content">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {markdown}
      </ReactMarkdown>
    </article>
  );
}
