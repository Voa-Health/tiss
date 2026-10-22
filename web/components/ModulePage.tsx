"use client";

import { Card, Col, Flex, Row, Typography, theme } from "antd";
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
import { PageStack } from "@/components/ui/PageStack";
import { Section } from "@/components/ui/Section";

export function ModulePage({ slug }: { slug: ModuleSlug }) {
  const { token } = theme.useToken();
  const content = moduleContent[slug];
  const price = launchPrices[slug];
  const priceText = formatLaunchPrice(price);

  return (
    <PageStack>
      <Row gutter={[token.marginXL, token.marginXL]}>
        <Col xs={24} lg={14}>
          <Section id="modulo" level={1} title={content.title} description={content.description}>
            <ul style={{ margin: 0, paddingInlineStart: token.paddingLG }}>
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
            <Card size="small">
              <Flex vertical gap={token.marginXXS}>
                {price.amount === null ? (
                  <Typography.Text strong>{pendingPriceLabel}</Typography.Text>
                ) : (
                  <>
                    <Typography.Text type="secondary">{launchPriceLabel}</Typography.Text>
                    <Typography.Title level={3} style={{ margin: 0 }}>{priceText}</Typography.Title>
                  </>
                )}
                {price.note && <Typography.Text type="secondary">{price.note}</Typography.Text>}
                <Typography.Text type="secondary">{content.status}</Typography.Text>
              </Flex>
            </Card>
          </Section>
        </Col>
        <Col xs={24} lg={10}>
          <Card>
            <WaitlistForm module={slug} />
          </Card>
        </Col>
      </Row>
      <Row gutter={[token.margin, token.margin]}>
        <Col xs={24} md={12}>
          <Card title="Hospedagem" style={{ height: "100%" }}>
            <Typography.Paragraph style={{ margin: 0 }}>{hostingText}</Typography.Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <OpenLibraryCard />
        </Col>
      </Row>
    </PageStack>
  );
}
