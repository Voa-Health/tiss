"use client";

import { Button, Card, Flex, Space, Tag, theme, Typography } from "antd";
import { NetworkSearch } from "@/components/NetworkSearch";
import { EmptyState } from "@/components/ui/EmptyState";
import type { RulePack } from "@/lib/rule-packs";
import { site } from "@/lib/site";
import { track } from "@/lib/analytics";

export function OperatorsContent({ packs }: { packs: RulePack[] }) {
  const { token } = theme.useToken();
  if (!packs.length) {
    return (
      <>
        <Typography.Title>Operadoras</Typography.Title>
        <NetworkSearch />
        <EmptyState
          title="Nenhum pacote público disponível"
          description="Contribua com regras públicas para operadoras."
          action={
            <Space wrap>
              <Button href="/docs/regras-operadora">Como criar um pacote</Button>
              <Button
                type="primary"
                href={site.operatorContactUrl}
                onClick={() => track("tiss_cta_github", { local: "operadoras" })}
              >
                Sugerir pacote
              </Button>
            </Space>
          }
        />
      </>
    );
  }

  return (
      <>
        <Typography.Title>Operadoras</Typography.Title>
        <Flex vertical gap={token.marginLG}>
          <NetworkSearch />
          {packs.map((pack) => (
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
          ))}
        </Flex>
    </>
  );
}
