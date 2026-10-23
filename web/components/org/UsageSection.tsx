"use client";

import { Alert, Button, Card, Col, Flex, Result, Row, Skeleton, Statistic, Table, Tag, theme, Typography } from "antd";
import type { TableColumnsType } from "antd";
import { EmptyState } from "@/components/ui/EmptyState";
import { useRecurso } from "@/lib/org/cliente";
import { brl, dia, inteiro } from "@/lib/org/formato";
import type { Uso } from "@/lib/org/tipos";

const DIAS = 30;
const GRATIS = "__gratis";

type Serie = { chave: string; rotulo: string; cor: string };
type LinhaDaChave = { key_id: string; name: string; prefix: string; revoked: boolean; cobradas: number; gratis: number };

function diasDoPeriodo(fim: string | null): string[] {
  const ultimo = fim ? new Date(`${fim.slice(0, 10)}T00:00:00Z`) : new Date();
  const base = Number.isNaN(ultimo.getTime()) ? new Date() : ultimo;
  return Array.from({ length: DIAS }, (_, indice) => {
    const data = new Date(base);
    data.setUTCDate(base.getUTCDate() - (DIAS - 1 - indice));
    return data.toISOString().slice(0, 10);
  });
}

function GraficoPorDia({ uso, series }: { uso: Uso; series: Serie[] }) {
  const { token } = theme.useToken();
  const dias = diasDoPeriodo(uso.period_end);
  const valores = new Map<string, Map<string, number>>();
  const somar = (data: string, serie: string, quantidade: number) => {
    const doDia = valores.get(data.slice(0, 10)) ?? new Map<string, number>();
    doDia.set(serie, (doDia.get(serie) ?? 0) + quantidade);
    valores.set(data.slice(0, 10), doDia);
  };
  uso.by_day.forEach((linha) => somar(linha.day, linha.kind, linha.quantity));
  uso.free_calls.by_day.forEach((linha) => somar(linha.day, GRATIS, linha.quantity));
  const totais = dias.map((data) => [...(valores.get(data)?.values() ?? [])].reduce((soma, valor) => soma + valor, 0));
  const maximo = Math.max(1, ...totais);
  const base = 190;
  const altura = 160;
  const passo = 880 / DIAS;
  const resumo = `Chamadas por dia nos últimos ${DIAS} dias; total ${inteiro(totais.reduce((a, b) => a + b, 0))}.`;

  return (
    <Card title="Por dia">
      <Flex vertical gap={token.margin}>
        <svg viewBox="0 0 900 220" role="img" aria-label={resumo} style={{ display: "block", width: "100%", height: "auto" }}>
          <line x1="8" y1={base} x2="892" y2={base} stroke={token.colorBorderSecondary} strokeWidth={token.lineWidth} />
          {dias.map((data, indice) => {
            let y = base;
            return (
              <g key={data}>
                <title>{`${dia(data)}: ${inteiro(totais[indice])}`}</title>
                {series.map((serie) => {
                  const h = ((valores.get(data)?.get(serie.chave) ?? 0) / maximo) * altura;
                  y -= h;
                  return <rect key={serie.chave} x={14 + indice * passo} y={y} width={passo * 0.6} height={h} fill={serie.cor} />;
                })}
                {indice % 5 === 0 && (
                  <text x={14 + indice * passo} y={base + 18} fontSize="12" fill={token.colorTextSecondary}>{dia(data)}</text>
                )}
              </g>
            );
          })}
        </svg>
        <Flex wrap gap={token.margin}>
          {series.map((serie) => (
            <Flex key={serie.chave} align="center" gap={token.marginXS}>
              <span aria-hidden style={{ width: token.sizeXS, height: token.sizeXS, borderRadius: token.borderRadiusXS, background: serie.cor }} />
              <Typography.Text>{serie.rotulo}</Typography.Text>
            </Flex>
          ))}
        </Flex>
      </Flex>
    </Card>
  );
}

function linhasPorChave(uso: Uso): LinhaDaChave[] {
  const linhas = new Map<string, LinhaDaChave>();
  const de = (item: Uso["by_key"][number]) =>
    linhas.get(item.key_id) ?? { key_id: item.key_id, name: item.name, prefix: item.prefix, revoked: item.revoked, cobradas: 0, gratis: 0 };
  uso.by_key.forEach((item) => linhas.set(item.key_id, { ...de(item), cobradas: item.quantity }));
  uso.free_calls.by_key.forEach((item) => linhas.set(item.key_id, { ...de(item), gratis: item.quantity }));
  return [...linhas.values()].sort((a, b) => b.cobradas + b.gratis - (a.cobradas + a.gratis));
}

export function UsageSection({ podeVer, rotuloFinanceiro }: { podeVer: boolean; rotuloFinanceiro: string }) {
  const { token } = theme.useToken();
  const uso = useRecurso<Uso>(podeVer ? `tiss/org/usage/?days=${DIAS}` : null);

  if (!podeVer) {
    return (
      <Card>
        <EmptyState
          title="Uso restrito"
          description={`O uso e o custo estimado aparecem para quem tem a Área Administração ou ${rotuloFinanceiro}.`}
        />
      </Card>
    );
  }
  if (uso.erro) {
    return (
      <Result status="error" title="Não foi possível carregar o uso." subTitle={uso.erro.message}
        extra={<Button onClick={uso.recarregar}>Tentar de novo</Button>} />
    );
  }
  if (uso.carregando || !uso.dados) return <Card><Skeleton active /></Card>;

  const dados = uso.dados;
  const paleta = [token.colorPrimary, token.colorSuccess, token.colorWarning, token.colorInfo, token.colorError];
  const series: Serie[] = [
    ...dados.by_operation.map((operacao, indice) => ({ chave: operacao.kind, rotulo: operacao.label, cor: paleta[indice % paleta.length] })),
    { chave: GRATIS, rotulo: "Operações grátis", cor: token.colorTextQuaternary },
  ];
  const cobradas = dados.by_operation.reduce((soma, item) => soma + item.quantity, 0);
  const guiasGratis = dados.by_operation.reduce((soma, item) => soma + item.free_quantity, 0);
  const vazio = cobradas === 0 && dados.free_calls.total === 0;

  const colunasDeOperacao: TableColumnsType<Uso["by_operation"][number]> = [
    { title: "Operação", dataIndex: "label", key: "label" },
    { title: "Quantidade", dataIndex: "quantity", key: "quantity", align: "right", render: inteiro },
    { title: "Na franquia", dataIndex: "free_quantity", key: "free_quantity", align: "right", render: inteiro },
    { title: "Preço unitário", dataIndex: "unit_price_brl", key: "unit_price_brl", align: "right", render: brl },
    { title: "Custo estimado", dataIndex: "estimated_cost_brl", key: "estimated_cost_brl", align: "right", render: brl },
  ];
  const colunasGratis: TableColumnsType<Uso["free_calls"]["by_operation"][number]> = [
    { title: "Operação", dataIndex: "operation", key: "operation", render: (valor: string) => <Typography.Text code>{valor}</Typography.Text> },
    { title: "Chamadas", dataIndex: "quantity", key: "quantity", align: "right", render: inteiro },
  ];
  const colunasDeChave: TableColumnsType<LinhaDaChave> = [
    {
      title: "Chave",
      key: "chave",
      render: (_, linha) => (
        <Flex wrap align="center" gap={token.marginXS}>
          <Typography.Text>{linha.name}</Typography.Text>
          <Typography.Text code>{linha.prefix}</Typography.Text>
          {linha.revoked && <Tag>Revogada</Tag>}
        </Flex>
      ),
    },
    { title: "Cobradas", dataIndex: "cobradas", key: "cobradas", align: "right", render: inteiro },
    { title: "Grátis", dataIndex: "gratis", key: "gratis", align: "right", render: inteiro },
  ];

  return (
    <Flex vertical gap={token.marginLG}>
      <Row gutter={[token.margin, token.margin]}>
        {[
          { titulo: `Custo estimado (${DIAS} dias)`, valor: brl(dados.estimated_total_brl) },
          { titulo: "Chamadas cobradas", valor: inteiro(cobradas) },
          { titulo: "Guias na franquia", valor: inteiro(guiasGratis) },
          { titulo: "Operações grátis", valor: inteiro(dados.free_calls.total) },
        ].map((item) => (
          <Col key={item.titulo} xs={24} sm={12} xl={6}>
            <Card style={{ height: "100%" }}><Statistic title={item.titulo} value={item.valor} /></Card>
          </Col>
        ))}
      </Row>
      <Alert
        type="info"
        showIcon
        title="O custo usa os preços de lançamento e as 1.000 guias grátis do cloud por mês. Validar, montar, hash e sandbox não são cobrados."
      />
      {vazio ? (
        <Card><EmptyState title="Sem uso no período" description="As chamadas feitas com as chaves da organização aparecem aqui." /></Card>
      ) : (
        <>
          <GraficoPorDia uso={dados} series={series} />
          <Card title="Por operação" styles={{ body: { display: "flex", flexDirection: "column", gap: token.margin } }}>
            <Table rowKey="kind" columns={colunasDeOperacao} dataSource={dados.by_operation} pagination={false} scroll={{ x: 640 }}
              locale={{ emptyText: "Nenhuma operação cobrada no período." }} />
            {dados.free_calls.by_operation.length > 0 && (
              <Table rowKey="operation" columns={colunasGratis} dataSource={dados.free_calls.by_operation} pagination={false}
                title={() => <Typography.Text strong>Operações grátis</Typography.Text>} />
            )}
          </Card>
          <Card title="Por chave">
            <Table rowKey="key_id" columns={colunasDeChave} dataSource={linhasPorChave(dados)} pagination={false} scroll={{ x: 520 }} />
          </Card>
        </>
      )}
    </Flex>
  );
}
