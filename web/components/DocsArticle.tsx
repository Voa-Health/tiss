"use client";

import { Card, Col, Row, Typography } from "antd";
import Link from "next/link";
import { MarkdownContent } from "@/components/MarkdownContent";

type DocumentLink = { slug: string; title: string };

export function DocsArticle({
  title,
  content,
  slug,
  documents,
}: {
  title: string;
  content: string;
  slug: string;
  documents: DocumentLink[];
}) {
  return (
    <>
      <Typography.Title>{title}</Typography.Title>
      <Row gutter={[24, 24]}>
        <Col xs={24} md={6}>
          <Card title="Documentação">
            {documents.map((item) => (
              <Typography.Paragraph key={item.slug}>
                <Link href={`/docs/${item.slug}`}>{item.title}</Link>
              </Typography.Paragraph>
            ))}
          </Card>
        </Col>
        <Col xs={24} md={18}>
          <MarkdownContent content={content} sourcePath={`docs/${slug}.md`} title={title} />
        </Col>
      </Row>
    </>
  );
}
