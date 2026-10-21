import type { Metadata } from "next";
import { ContentIndex } from "@/components/ContentIndex";
import { readDocs } from "@/lib/content";

export const metadata: Metadata = {
  title: "Documentação",
  description: "Guias e referências para validar e operar documentos TISS.",
};

export default function DocsIndex() {
  const items = readDocs().map(({ slug, title }) => ({ slug, title }));
  return (
    <ContentIndex
      title="Documentação"
      description="Guias técnicos da biblioteca voa-tiss."
      items={items}
      hrefPrefix="/docs"
    />
  );
}
