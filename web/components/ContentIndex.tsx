"use client";

import { Card, Flex, theme, Typography } from "antd";
import Link from "next/link";

type ContentItem = { slug: string; title: string };

export function ContentIndex({
  title,
  description,
  items,
  hrefPrefix,
}: {
  title: string;
  description: string;
  items: ContentItem[];
  hrefPrefix: string;
}) {
  const { token } = theme.useToken();
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
