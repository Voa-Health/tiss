"use client";

import { Alert, Button, Card, Flex, Skeleton, Table, Tag, theme, Typography } from "antd";
import type { TableColumnsType } from "antd";
import { useRecurso, type Recurso } from "@/lib/org/cliente";
import { brlUnitario, inteiro } from "@/lib/org/formato";
import { caminhoDosPrecos, ehPago, NOMES_DOS_PRODUTOS, PRODUTOS, type ItemDePreco, type Produto, type TabelaDePrecos } from "@/lib/org/produtos";

export function useTabelasDePrecos(): Record<Produto, Recurso<TabelaDePrecos>> {
  return {
    tiss: useRecurso<TabelaDePrecos>(caminhoDosPrecos("tiss")),
    terminology: useRecurso<TabelaDePrecos>(caminhoDosPrecos("terminology")),
    rnds: useRecurso<TabelaDePrecos>(caminhoDosPrecos("rnds")),
    sncr: useRecurso<TabelaDePrecos>(caminhoDosPrecos("sncr")),
  };
}

export function tabelasCarregadas(tabelas: Record<Produto, Recurso<TabelaDePrecos>>): TabelaDePrecos[] {
  return PRODUTOS.flatMap((produto) => tabelas[produto].dados ?? []);
}

const COLUNAS: TableColumnsType<ItemDePreco> = [
  { title: "Item", dataIndex: "label", key: "label" },
  {
    title: "Preço",
    key: "preco",
    render: (_, item) => (ehPago(item) ? `${brlUnitario(item.unit_amount)} por ${item.unit}` : <Tag>Grátis</Tag>),
  },
  {
    title: "Franquia mensal",
    dataIndex: "monthly_free",
    key: "monthly_free",
    align: "right",
    render: (valor: number, item) => (ehPago(item) && valor > 0 ? `${inteiro(valor)} ${item.unit}` : "—"),
  },
];

export function PrecosDosProdutos({ tabelas }: { tabelas: Record<Produto, Recurso<TabelaDePrecos>> }) {
  const { token } = theme.useToken();
  return (
    <Card title="Preços por produto">
      <Flex vertical gap={token.marginLG}>
        {PRODUTOS.map((produto) => {
          const tabela = tabelas[produto];
          return (
            <Flex key={produto} vertical gap={token.marginSM}>
              <Typography.Text strong>{NOMES_DOS_PRODUTOS[produto]}</Typography.Text>
              {tabela.carregando ? <Skeleton active paragraph={{ rows: 2 }} /> : tabela.erro ? (
                <Alert
                  type="warning"
                  title={`Não foi possível carregar os preços de ${NOMES_DOS_PRODUTOS[produto]}.`}
                  action={<Button onClick={tabela.recarregar}>Atualizar</Button>}
                />
              ) : (
                <Table
                  rowKey="kind"
                  pagination={false}
                  columns={COLUNAS}
                  scroll={{ x: 520 }}
                  dataSource={tabela.dados?.items ?? []}
                />
              )}
            </Flex>
          );
        })}
      </Flex>
    </Card>
  );
}
