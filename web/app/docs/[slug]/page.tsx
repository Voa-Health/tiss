import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DocsArticle } from "@/components/DocsArticle";
import { readDoc, readDocs } from "@/lib/content";

export function generateStaticParams() {
  return readDocs().map(({ slug }) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const doc = readDoc(slug);
  return { title: doc?.title ?? "Documentação", description: `Guia técnico: ${doc?.title ?? "voa-tiss"}.` };
}

export default async function DocPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const doc = readDoc(slug);
  if (!doc) notFound();
  const docs = readDocs();

  return <DocsArticle title={doc.title} content={doc.content} slug={doc.slug} documents={docs} />;
}
