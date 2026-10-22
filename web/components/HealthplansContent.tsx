"use client";

import { Button, Card, Col, Flex, Row, Space, Tag, theme, Typography } from "antd";
import { FeatureCard } from "@/components/FeatureCard";
import { NetworkSearch } from "@/components/NetworkSearch";
import { Section } from "@/components/ui/Section";
import { EmptyState } from "@/components/ui/EmptyState";
import { healthplanFeatures, healthplanModules } from "@/lib/audiences";
import { formatLaunchPrice, launchPrices, moduleContent } from "@/lib/modules";
import type { RulePack } from "@/lib/rule-packs";
import { docsPageUrl, site } from "@/lib/site";
import { track } from "@/lib/analytics";

function HealthplanFeatures() {
  const { token } = theme.useToken();
  const withDemo = healthplanFeatures.filter((feature) => feature.demo);
  const withoutDemo = healthplanFeatures.filter((feature) => !feature.demo);
  return (
    <Section id="para-operadoras" title="Para operadoras">
      <Flex vertical gap={token.margin}>
        {withDemo.map((feature) => (
          <FeatureCard key={feature.label} item={feature} />
        ))}
        {withoutDemo.length > 0 && (
          <Row gutter={[token.margin, token.margin]}>
            {withoutDemo.map((feature) => (
              <Col key={feature.label} xs={24} md={12}>
                <FeatureCard item={feature} />
              </Col>
            ))}
          </Row>
        )}
      </Flex>
    </Section>
  );
}

function HealthplanModules() {
  const { token } = theme.useToken();
  return (
    <Section id="modulos-para-operadoras" title="Módulos para operadoras">
      <Row gutter={[token.margin, token.margin]}>
        {healthplanModules.map((slug) => (
          <Col key={slug} xs={24} md={12}>
            <Card style={{ height: "100%" }}>
              <Flex vertical gap={token.marginSM} align="flex-start">
                <Typography.Title level={3} style={{ margin: 0, fontSize: token.fontSizeHeading4 }}>
                  {moduleContent[slug].title}
                </Typography.Title>
                <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
                  {moduleContent[slug].description}
                </Typography.Paragraph>
                <Typography.Text strong>{formatLaunchPrice(launchPrices[slug])}</Typography.Text>
                <Button href={moduleContent[slug].href}>Entrar na lista de espera</Button>
              </Flex>
            </Card>
          </Col>
        ))}
      </Row>
    </Section>
  );
}

export function HealthplansContent({ packs }: { packs: RulePack[] }) {
  const { token } = theme.useToken();
  return (
    <>
      <Section
        id="operadoras"
        level={1}
        title="Operadoras"
        description="A camada aberta roda na sua infraestrutura, sem contrato e sem enviar dado à Voa. Os módulos com agente decidem sempre com a regra ou a evidência citada."
      />
      <HealthplanFeatures />
      <HealthplanModules />
      <NetworkSearch />
      <Section id="pacotes-de-regras" title="Pacotes de regras públicos">
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
                <Button href={docsPageUrl("regras-operadora")}>Como criar um pacote</Button>
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
      </Section>
    </>
  );
}
