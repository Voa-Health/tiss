"use client";

import { Button, Card, Descriptions, Flex, Grid, theme, Typography } from "antd";
import { EmptyState } from "@/components/ui/EmptyState";
import type { TissSettings } from "@/lib/org-mock";
import type { RulePack } from "@/lib/rule-packs";

export function TissSection({
  settings,
  packs,
}: {
  settings: TissSettings;
  packs: RulePack[];
}) {
  const screens = Grid.useBreakpoint();
  const { token } = theme.useToken();
  const inUse = packs.filter((pack) => {
    const registries = [pack.mantenedor.registro_ans, pack.operadora].filter(
      (registry): registry is string => Boolean(registry),
    );
    return registries.some((registry) => settings.operadoras_em_uso.includes(registry));
  });

  return (
    <Flex vertical gap="var(--ant-margin-lg)">
      <Card title="Configurações TISS">
        <Descriptions
          bordered
          column={1}
          layout={screens.md ? "horizontal" : "vertical"}
          items={[
            { key: "standard", label: "Padrão TISS", children: settings.padrao },
            {
              key: "guides",
              label: "Máx. de guias por lote",
              children: settings.max_guias_por_lote,
            },
          ]}
        />
      </Card>
      <Card title="Operadoras em uso">
        {inUse.length ? (
          <Flex vertical gap="var(--ant-margin)">
            {inUse.map((pack) => {
              const registro = pack.mantenedor.registro_ans ?? pack.operadora;
              return (
                <Flex
                  key={pack.operadora}
                  wrap
                  justify="space-between"
                  align="center"
                  gap="var(--ant-margin)"
                >
                  <Typography.Text>
                    {pack.razaoSocial} · Registro {registro} · {pack.regras.length} regras
                  </Typography.Text>
                  <Button href="/operadoras">Ver pacotes</Button>
                </Flex>
              );
            })}
          </Flex>
        ) : (
          <EmptyState
            title="Nenhuma regra de operadora no pacote"
            description={
              <Typography.Text style={{ color: token.colorTextSecondary }}>
                Consulte os pacotes disponíveis para esta organização.
              </Typography.Text>
            }
            action={<Button href="/operadoras">Consultar operadoras</Button>}
          />
        )}
      </Card>
    </Flex>
  );
}
