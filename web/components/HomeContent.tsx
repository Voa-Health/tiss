"use client";

import { ArrowDownOutlined, ArrowRightOutlined, RollbackOutlined } from "@ant-design/icons";
import { Button, Card, Col, Flex, Grid, Row, Space, Typography, theme } from "antd";
import Link from "next/link";
import { Fragment } from "react";
import { CodeBlock } from "./CodeBlock";
import { site } from "@/lib/site";
import { track } from "@/lib/analytics";
import { audiences } from "@/lib/audiences";
import { formatLaunchPrice, launchPrices, moduleContent } from "@/lib/modules";

export function HomeContent() {
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const steps = [
    { number: "01", title: "Validar", description: "Identifique inconsistências no lote TISS." },
    { number: "02", title: "Corrigir", description: "Revise os achados e ajuste o XML." },
    { number: "03", title: "Revalidar", description: "Confirme o lote antes do envio." },
  ];

  return (
    <Flex vertical gap={token.paddingXL}>
      <section>
        <Typography.Title>TISS aberto para quem envia e para quem recebe</Typography.Title>
        <Typography.Paragraph>
          Valide, gere e audite TISS offline, simule a operadora, consulte dados abertos da ANS e
          integre agentes por MCP.
        </Typography.Paragraph>
        <Space wrap>
          <Button type="primary" size="large" href="/playground">Experimentar playground</Button>
          <Button size="large" href={site.docsUrl}>Consultar documentação</Button>
        </Space>
      </section>

      <section aria-labelledby="para-quem-e">
        <Typography.Title level={2} id="para-quem-e">Para quem é</Typography.Title>
        <Row gutter={[token.marginLG, token.marginLG]}>
          {audiences.map((audience) => (
            <Col key={audience.id} xs={24} lg={12}>
              <Card id={audience.id} title={audience.title} style={{ height: "100%" }}>
                <Flex vertical gap={token.margin}>
                  <Typography.Paragraph style={{ margin: 0 }}>{audience.summary}</Typography.Paragraph>
                  <ul style={{ margin: 0, paddingInlineStart: token.paddingLG }}>
                    {audience.items.map((item) => (
                      <li key={item.label}>
                        <Link href={item.href}>{item.label}</Link>
                        <Typography.Text type="secondary">: {item.description}</Typography.Text>
                      </li>
                    ))}
                  </ul>
                  {audience.modules.length > 0 && (
                    <Flex vertical gap={token.marginXS}>
                      <Typography.Text strong>Módulos</Typography.Text>
                      {audience.modules.map((slug) => (
                        <Typography.Text key={slug}>
                          <Link href={moduleContent[slug].href}>{moduleContent[slug].label}</Link>
                          <Typography.Text type="secondary">
                            {" "}· {formatLaunchPrice(launchPrices[slug])}
                          </Typography.Text>
                        </Typography.Text>
                      ))}
                    </Flex>
                  )}
                  <div>
                    <Button href={audience.cta.href}>{audience.cta.label}</Button>
                  </div>
                </Flex>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      <section aria-labelledby="como-funciona">
        <Typography.Title level={2} id="como-funciona">Como funciona para quem envia</Typography.Title>
        <Flex vertical gap={token.margin}>
          <Flex vertical={!screens.md} align="stretch" gap={token.marginSM}>
            {steps.map((step, index) => (
              <Fragment key={step.number}>
                <Card style={{ flex: screens.md ? "1 1 0" : undefined, minWidth: 0 }}>
                  <Typography.Text type="secondary">{step.number}</Typography.Text>
                  <Typography.Title level={3}>{step.title}</Typography.Title>
                  <Typography.Paragraph>{step.description}</Typography.Paragraph>
                </Card>
                {index < steps.length - 1 && (
                  <Flex
                    flex="none"
                    align="center"
                    justify="center"
                    aria-hidden="true"
                    style={{
                      paddingInline: screens.md ? token.paddingXS : 0,
                      paddingBlock: screens.md ? 0 : token.paddingXS,
                    }}
                  >
                    {screens.md ? <ArrowRightOutlined /> : <ArrowDownOutlined />}
                  </Flex>
                )}
              </Fragment>
            ))}
          </Flex>
          <Flex justify="center" align="center" gap={token.marginSM}>
            <RollbackOutlined />
            <Typography.Text>O resultado retorna à validação</Typography.Text>
          </Flex>
        </Flex>
      </section>

      <Row gutter={[token.marginLG, token.marginLG]}>
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
      <Space wrap aria-label="Recursos">
        {[
          { href: site.docsUrl, label: "Docs" },
          { href: "/tutoriais", label: "Tutoriais" },
          { href: "/api", label: "API" },
          { href: "/playground", label: "Playground" },
          { href: site.github, label: "GitHub", local: "home" },
          { href: site.pypi, label: "PyPI" },
        ].map((link) => (
          <Link
            key={link.href}
            href={link.href}
            onClick={
              link.href === site.github
                ? () => track("tiss_cta_github", { local: "home" })
                : undefined
            }
          >
            {link.label}
          </Link>
        ))}
      </Space>
    </Flex>
  );
}
