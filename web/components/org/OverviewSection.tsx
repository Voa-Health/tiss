"use client";

import { CheckCircleFilled } from "@ant-design/icons";
import { Alert, Card, Descriptions, Flex, Grid, Tag, theme, Typography } from "antd";
import { formatDate } from "@/lib/site";
import { maskCnpj, type Org } from "@/lib/org-mock";

const typeLabels = {
  prov: "Prestador",
  pay: "Operadora",
  bus: "Empresa/healthtech",
} as const;

export function OverviewSection({ org }: { org: Org }) {
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const items = [
    { key: "name", label: "Nome", children: org.nome },
    {
        key: "cnpj",
        label: "CNPJ",
        children: (
          <Flex wrap align="center" gap={token.marginSM}>
          <Typography.Text code style={{ whiteSpace: "nowrap" }}>
            {maskCnpj(org.cnpj)}
          </Typography.Text>
          {org.cnpj_verificado && (
            <Tag
              color="success"
              icon={<CheckCircleFilled />}
              style={{ color: token.colorText }}
            >
              CNPJ verificado
            </Tag>
          )}
        </Flex>
      ),
    },
    { key: "type", label: "Tipo", children: typeLabels[org.tipo] },
    ...(org.tipo === "pay" && org.registro_ans
      ? [{ key: "ans", label: "Registro ANS", children: org.registro_ans }]
      : []),
    {
      key: "terms",
      label: "Termos",
      children: org.termos
        ? `Versão ${org.termos.versao}, aceitos por ${org.termos.aceito_por} em ${formatDate(org.termos.aceito_em)}`
        : "Não aceitos",
    },
  ];

  return (
    <Card title="Dados da organização">
      {org.termos ? (
        <Descriptions
          bordered
          column={1}
          layout={screens.md ? "horizontal" : "vertical"}
          items={items}
        />
      ) : (
        <Flex vertical gap={token.margin}>
          <Descriptions
            bordered
            column={1}
            layout={screens.md ? "horizontal" : "vertical"}
            items={items.filter((item) => item.key !== "terms")}
          />
          <Alert type="warning" showIcon title="Os termos da organização não foram aceitos." />
        </Flex>
      )}
    </Card>
  );
}
