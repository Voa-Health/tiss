import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MarkdownContent } from "@/components/MarkdownContent";
import { readTutorial, readTutorials, tutorialMarkdown } from "@/lib/content";

export function generateStaticParams() {
  return readTutorials().map(({ slug }) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const tutorial = readTutorial(slug);
  return {
    title: tutorial?.title ?? "Tutoriais",
    description: `Tutorial técnico: ${tutorial?.title ?? "voa-tiss"}.`,
  };
}

export default async function TutorialPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const tutorial = readTutorial(slug);
  if (!tutorial) notFound();
  return (
    <MarkdownContent
      content={tutorialMarkdown(tutorial)}
      sourcePath={`docs/tutoriais/${tutorial.slug}.ipynb`}
    />
  );
}
