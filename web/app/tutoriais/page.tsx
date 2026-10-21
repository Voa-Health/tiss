import type { Metadata } from "next";
import { ContentIndex } from "@/components/ContentIndex";
import { readTutorials } from "@/lib/content";

export const metadata: Metadata = {
  title: "Tutoriais",
  description: "Exemplos executados para trabalhar com lotes e dados TISS.",
};

export default function TutorialsIndex() {
  const items = readTutorials().map(({ slug, title }) => ({ slug, title }));
  return (
    <ContentIndex
      title="Tutoriais"
      description="Exemplos executados com dados sintéticos."
      items={items}
      hrefPrefix="/tutoriais"
    />
  );
}
