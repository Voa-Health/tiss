"use client";

import { Button, Card, Col, Flex, Row, Space, Tag, theme, Typography } from "antd";
import Link from "next/link";
import { NetworkSearch } from "@/components/NetworkSearch";
import { EmptyState } from "@/components/ui/EmptyState";
import { healthplanFeatures, healthplanModules } from "@/lib/audiences";
import { formatLaunchPrice, launchPrices, moduleContent } from "@/lib/modules";
import type { RulePack } from "@/lib/rule-packs";
import { site } from "@/lib/site";
import { track } from "@/lib/analytics";

function HealthplanFeatures() {
  const { token } = theme.useToken();
  return (
    <section aria-labelledby="para-operadoras">
      <Typography.Title level={2} id="para-operadoras">Para operadoras</Typography.Title>
      <Typography.Paragraph>
        A camada aberta roda na sua infraestrutura, sem contrato e sem enviar dado à Voa. Os
        módulos com agente decidem sempre com a regra ou a evidência citada.
      </Typography.Paragraph>
      <Row gutter={[token.margin, token.margin]}>
        {healthplanFeatures.map((feature) => (
          <Col key={feature.label} xs={24} md={12} lg={8}>
            <Card title={feature.label} style={{ height: "100%" }}>
              <Typography.Paragraph>{feature.description}</Typography.Paragraph>
              <Link href={feature.href}>{feature.linkLabel}</Link>
            </Card>
          </Col>
        ))}
      </Row>
      <Typography.Title level={3} style={{ marginBlockStart: token.marginLG }}>
        Módulos para operadoras
      </Typography.Title>
      <Row gutter={[token.margin, token.margin]}>
        {healthplanModules.map((slug) => (
          <Col key={slug} xs={24} md={12}>
            <Card title={moduleContent[slug].title} style={{ height: "100%" }}>
              <Typography.Paragraph>{moduleContent[slug].description}</Typography.Paragraph>
              <Typography.Paragraph strong>
                {formatLaunchPrice(launchPrices[slug])}
              </Typography.Paragraph>
              <Button href={moduleContent[slug].href}>Entrar na lista de espera</Button>
            </Card>
          </Col>
        ))}
      </Row>
    </section>
  );
}

export function HealthplansContent({ packs }: { packs: RulePack[] }) {
  const { token } = theme.useToken();
  return (
    <>
      <Typography.Title>Operadoras</Typography.Title>
      <Flex vertical gap={token.marginLG}>
        <HealthplanFeatures />
        <NetworkSearch />
        {packs.length ? (
          packs.map((pack) => (
            <Card
              key={pack.operadora}
              title={`${pack.operadora} · ${pack.razaoSocial}`}
              style={{ width: "100%" }}
            >
              <Typography.Paragraph>
                Mantenedor: {pack.mantenedor.tipo} · TISS {pack.versao_tiss}{" "}
                <Tag color={pack.official ? "green" : "default"}>
                  {pack.official ? "Oficial" : "Comunidade"}
                </Tag>
              </Typography.Paragraph>
              <Flex vertical gap={token.marginSM}>
                {pack.regras.map((rule) => (
                  <div key={rule.id}>
                    <span>
                      {rule.id} · {rule.descricao} · {rule.severity} ·{" "}
                      <a href={rule.source.url}>fonte</a>
                    </span>
                  </div>
                ))}
              </Flex>
            </Card>
          ))
        ) : (
          <EmptyState
            title="Nenhum pacote público disponível"
            description="Contribua com regras públicas para operadoras."
            action={
              <Space wrap>
                <Button href={`${site.docsUrl}/regras-operadora`}>Como criar um pacote</Button>
                <Button
                  type="primary"
                  href={site.healthplanContactUrl}
                  onClick={() => track("tiss_cta_github", { local: "operadoras" })}
                >
                  Sugerir pacote
                </Button>
              </Space>
            }
          />
        )}
      </Flex>
    </>
  );
}
