"use client";

import { Card, Col, Flex, Row, theme, Typography } from "antd";
import Link from "next/link";
import { Section } from "@/components/ui/Section";

type ContentItem = { slug: string; title: string };

export function ContentIndex({
  title,
  description,
  items,
  hrefPrefix,
  variant = "list",
}: {
  title: string;
  description: string;
  items: ContentItem[];
  hrefPrefix: string;
  variant?: "list" | "grid";
}) {
  const { token } = theme.useToken();
  if (variant === "grid") {
    return (
      <Section id="indice" level={1} title={title} description={description}>
        <Row gutter={[token.margin, token.margin]}>
          {items.map((item) => (
            <Col key={item.slug} xs={24} md={12} lg={8}>
              <Card style={{ height: "100%" }}>
                <Link href={`${hrefPrefix}/${item.slug}`}>{item.title}</Link>
              </Card>
            </Col>
          ))}
        </Row>
      </Section>
    );
  }
  return (
    <>
      <Typography.Title>{title}</Typography.Title>
      <Typography.Paragraph>{description}</Typography.Paragraph>
      <Card>
        <Flex vertical gap={token.margin}>
          {items.map((item) => (
            <div key={item.slug}>
              <Link href={`${hrefPrefix}/${item.slug}`}>{item.title}</Link>
            </div>
          ))}
        </Flex>
      </Card>
    </>
  );
}
