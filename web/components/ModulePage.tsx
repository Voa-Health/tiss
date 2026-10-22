"use client";

import { Card, Flex, Typography, theme } from "antd";
import Link from "next/link";
import { OpenLibraryCard } from "@/components/OpenLibraryCard";
import {
  formatLaunchPrice,
  hostingText,
  launchPriceLabel,
  launchPrices,
  moduleContent,
  pendingPriceLabel,
  type ModuleSlug,
} from "@/lib/modules";
import { WaitlistForm } from "@/components/WaitlistForm";

export function ModulePage({ slug }: { slug: ModuleSlug }) {
  const { token } = theme.useToken();
  const content = moduleContent[slug];
  const price = launchPrices[slug];
  const priceText = formatLaunchPrice(price);

  return (
    <Flex vertical gap={token.paddingXL}>
      <section>
        <Typography.Title>{content.title}</Typography.Title>
        <Typography.Paragraph>{content.description}</Typography.Paragraph>
        <ul>
          {content.points.map((point) => (
            <li key={point}>
              {slug === "recurso" && point.includes("calculadora") ? (
                <>Compare cenários na <Link href="/calculadora">calculadora de economia mensal</Link>.</>
              ) : (
                point
              )}
            </li>
          ))}
        </ul>
        {price.amount === null ? (
          <Typography.Text strong>{pendingPriceLabel}</Typography.Text>
        ) : (
          <Flex vertical gap={4}>
            <Typography.Text type="secondary">{launchPriceLabel}</Typography.Text>
            <Typography.Title level={3} style={{ margin: 0 }}>{priceText}</Typography.Title>
          </Flex>
        )}
        {price.note && <Typography.Paragraph type="secondary">{price.note}</Typography.Paragraph>}
        <Typography.Paragraph type="secondary">{content.status}</Typography.Paragraph>
      </section>
      <Card title="Hospedagem">
        <Typography.Paragraph style={{ margin: 0 }}>{hostingText}</Typography.Paragraph>
      </Card>
      <OpenLibraryCard />
      <WaitlistForm module={slug} />
    </Flex>
  );
}
