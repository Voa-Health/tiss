"use client";

import { Descriptions, Flex, Table, theme, Typography } from "antd";
import Link from "next/link";
import {
  FONTE_CADOP,
  type FontePainel,
  formatValor,
  INDICADORES,
  type Operadora,
  type Semestre,
} from "@/lib/operadoras";

export function OperatorProfile({
  operadora,
  serie,
  fonte,
}: {
  operadora: Operadora;
  serie: Semestre[];
  fonte: FontePainel;
}) {
  const { token } = theme.useToken();
  const columns = [
    { title: "Semestre", dataIndex: "periodo", key: "periodo" },
    ...INDICADORES.map(({ chave, rotulo, unidade }, index) => ({
      title: `${rotulo} (${unidade})`,
      key: chave,
      align: "right" as const,
      render: (_: unknown, linha: Semestre) =>
        linha.inconsistentes.includes(chave) ? (
          <span style={{ color: token.colorWarningText }} title="Inconsistente">
            {formatValor(linha.valores[index])}*
          </span>
        ) : (
          formatValor(linha.valores[index])
        ),
    })),
  ];

  return (
    <>
      <Typography.Paragraph>
        <Link href="/operadoras">Operadoras</Link>
      </Typography.Paragraph>
      <Typography.Title>{operadora.razao_social}</Typography.Title>
      <Flex vertical gap={token.marginLG}>
        <Descriptions
          column={{ xs: 1, md: 2 }}
          items={[
            { key: "registro", label: "Registro ANS", children: operadora.registro_ans },
            { key: "fantasia", label: "Nome fantasia", children: operadora.nome_fantasia || "—" },
            { key: "modalidade", label: "Modalidade", children: operadora.modalidade },
            { key: "sede", label: "Sede", children: `${operadora.cidade}/${operadora.uf}` },
          ]}
        />
        <div>
          <Typography.Title level={2}>Indicadores semestrais</Typography.Title>
          {serie.length ? (
            <>
              <Typography.Paragraph>
                Período: {serie[0].periodo} a {serie[serie.length - 1].periodo}. Atualizado pela ANS em{" "}
                {fonte.atualizado_em}.
              </Typography.Paragraph>
              <Table
                rowKey="periodo"
                columns={columns}
                dataSource={serie}
                pagination={false}
                size="small"
                scroll={{ x: true }}
              />
              <Typography.Paragraph type="secondary" style={{ marginTop: token.marginSM }}>
                * Inconsistente: a ANS não publicou o valor ou ele passa de três vezes a mediana dos
                semestres anteriores da operadora, com salto de ao menos 10 pontos percentuais (30 dias
                no tempo médio de pagamento).
              </Typography.Paragraph>
            </>
          ) : (
            <Typography.Paragraph>A ANS não publica indicadores de glosa para esta operadora.</Typography.Paragraph>
          )}
        </div>
        <Typography.Paragraph type="secondary">
          Fonte:{" "}
          <a href={fonte.url}>
            ANS, Painel de Indicadores de Glosa ({fonte.licenca})
          </a>
          . Cadastro: <a href={FONTE_CADOP}>ANS, Operadoras de planos de saúde ativas (CC BY)</a>.
        </Typography.Paragraph>
      </Flex>
    </>
  );
}
