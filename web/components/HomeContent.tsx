"use client";

import { ArrowRightOutlined } from "@ant-design/icons";
import { Button, Card, Col, Flex, Row, Space, Typography, theme } from "antd";
import Link from "next/link";
import { CodeBlock } from "./CodeBlock";
import { TerminalGif } from "./FeatureDemos";
import { PageStack } from "@/components/ui/PageStack";
import { Section } from "@/components/ui/Section";
import { site } from "@/lib/site";
import { track } from "@/lib/analytics";
import { audiences, healthplanFeatures, type Audience } from "@/lib/audiences";

function AudienceCard({ audience }: { audience: Audience }) {
  const { token } = theme.useToken();
  return (
    <Card id={audience.id} style={{ height: "100%" }}>
      <Flex
        vertical
        gap={token.marginXS}
        align="flex-start"
        style={{ height: "100%" }}
      >
        <Typography.Title
          level={3}
          style={{ margin: 0, fontSize: token.fontSizeHeading4 }}
        >
          {audience.title}
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
          {audience.summary}
        </Typography.Paragraph>
        <Link
          href={audience.cta.href}
          style={{
            marginBlockStart: "auto",
            paddingBlockStart: token.paddingXS,
          }}
        >
          {audience.cta.label} <ArrowRightOutlined aria-hidden="true" />
        </Link>
      </Flex>
    </Card>
  );
}

export function HomeContent() {
  const { token } = theme.useToken();
  return (
    <PageStack>
      <Row gutter={[token.marginXL, token.marginXL]} align="middle">
        <Col xs={24} lg={11}>
          <Section
            id="inicio"
            level={1}
            title="TISS aberto para quem envia e para quem recebe"
            description="Valide, gere e audite TISS offline. Simule a operadora, consulte dados abertos da ANS e conecte agentes por MCP."
            extra={
              <Space wrap>
                <Button type="primary" size="large" href="/playground">
                  Experimentar playground
                </Button>
                <Button size="large" href={site.docsUrl}>
                  Documentação
                </Button>
              </Space>
            }
          />
        </Col>
        <Col xs={24} lg={13}>
          <TerminalGif item={healthplanFeatures[0]} priority />
        </Col>
      </Row>

      <Section id="para-quem-e" title="Para quem é">
        <Row gutter={[token.margin, token.margin]}>
          {audiences.map((audience) => (
            <Col key={audience.id} xs={24} sm={12} lg={6}>
              <AudienceCard audience={audience} />
            </Col>
          ))}
        </Row>
      </Section>

      <Section
        id="comece"
        title="Comece agora"
        extra={
          <Link
            href={site.github}
            onClick={() => track("tiss_cta_github", { local: "home" })}
          >
            Código no GitHub <ArrowRightOutlined aria-hidden="true" />
          </Link>
        }
      >
        <Row gutter={[token.margin, token.margin]}>
          <Col xs={24} md={12}>
            <Card title="Biblioteca Python">
              <CodeBlock code={site.installCommand} />
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="Cliente MCP">
              <CodeBlock code={site.mcpCommand} />
            </Card>
          </Col>
        </Row>
      </Section>
    </PageStack>
  );
}
