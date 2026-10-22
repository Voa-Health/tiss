"use client";

import { Button, Card, Col, Flex, Row, Space, Typography, theme } from "antd";
import Link from "next/link";
import { CodeBlock } from "./CodeBlock";
import { PageStack } from "@/components/ui/PageStack";
import { Section } from "@/components/ui/Section";
import { site } from "@/lib/site";
import { track } from "@/lib/analytics";
import { audiences, type Audience } from "@/lib/audiences";
import { formatLaunchPrice, launchPrices, moduleContent } from "@/lib/modules";

const steps = [
  { number: "01", title: "Validar", description: "Identifique inconsistências no lote TISS." },
  { number: "02", title: "Corrigir", description: "Revise os achados e ajuste o XML." },
  { number: "03", title: "Revalidar", description: "Confirme o lote antes do envio." },
];

function AudienceCard({ audience }: { audience: Audience }) {
  const { token } = theme.useToken();
  return (
    <Card id={audience.id} style={{ height: "100%" }}>
      <Flex vertical gap={token.margin} align="flex-start" style={{ height: "100%" }}>
        <Flex vertical gap={token.marginXXS}>
          <Typography.Title level={3} style={{ margin: 0, fontSize: token.fontSizeHeading4 }}>
            {audience.title}
          </Typography.Title>
          <Typography.Text type="secondary">{audience.summary}</Typography.Text>
        </Flex>
        <Flex vertical gap={token.marginSM} component="ul" style={{ margin: 0, padding: 0, listStyle: "none" }}>
          {audience.items.map((item) => (
            <li key={item.label}>
              <Link href={item.href}>{item.label}</Link>
              <Typography.Paragraph type="secondary" style={{ margin: 0, fontSize: token.fontSizeSM }}>
                {item.description}
              </Typography.Paragraph>
            </li>
          ))}
        </Flex>
        {audience.modules.length > 0 && (
          <Flex vertical gap={token.marginXXS}>
            <Typography.Text strong>Módulos</Typography.Text>
            {audience.modules.map((slug) => (
              <Typography.Text key={slug}>
                <Link href={moduleContent[slug].href}>{moduleContent[slug].label}</Link>
                <Typography.Text type="secondary"> · {formatLaunchPrice(launchPrices[slug])}</Typography.Text>
              </Typography.Text>
            ))}
          </Flex>
        )}
        <Button href={audience.cta.href} style={{ marginBlockStart: "auto" }}>
          {audience.cta.label}
        </Button>
      </Flex>
    </Card>
  );
}

function StepCard({ step }: { step: (typeof steps)[number] }) {
  const { token } = theme.useToken();
  return (
    <Card style={{ height: "100%" }}>
      <Flex vertical gap={token.marginXXS}>
        <Typography.Text type="secondary">{step.number}</Typography.Text>
        <Typography.Title level={3} style={{ margin: 0, fontSize: token.fontSizeHeading4 }}>
          {step.title}
        </Typography.Title>
        <Typography.Text type="secondary">{step.description}</Typography.Text>
      </Flex>
    </Card>
  );
}

export function HomeContent() {
  const { token } = theme.useToken();
  return (
    <PageStack>
      <Section
        id="inicio"
        level={1}
        title="TISS aberto para quem envia e para quem recebe"
        description="Valide, gere e audite TISS offline, simule a operadora, consulte dados abertos da ANS e integre agentes por MCP."
        extra={
          <Space wrap>
            <Button type="primary" size="large" href="/playground">
              Experimentar playground
            </Button>
            <Button size="large" href={site.docsUrl}>
              Consultar documentação
            </Button>
          </Space>
        }
      />

      <Section id="para-quem-e" title="Para quem é">
        <Row gutter={[token.margin, token.margin]}>
          {audiences.map((audience) => (
            <Col key={audience.id} xs={24} md={12}>
              <AudienceCard audience={audience} />
            </Col>
          ))}
        </Row>
      </Section>

      <Section
        id="como-funciona"
        title="Como funciona para quem envia"
        description="O resultado retorna à validação."
      >
        <Row gutter={[token.margin, token.margin]}>
          {steps.map((step) => (
            <Col key={step.number} xs={24} md={8}>
              <StepCard step={step} />
            </Col>
          ))}
        </Row>
      </Section>

      <Section
        id="comece"
        title="Comece agora"
        extra={
          <Link href={site.github} onClick={() => track("tiss_cta_github", { local: "home" })}>
            Código no GitHub
          </Link>
        }
      >
        <Row gutter={[token.margin, token.margin]}>
          <Col xs={24} md={12}>
            <Card title="Instale a biblioteca">
              <CodeBlock code={site.installCommand} />
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="Conecte um cliente MCP">
              <CodeBlock code={site.mcpCommand} />
            </Card>
          </Col>
        </Row>
      </Section>
    </PageStack>
  );
}
