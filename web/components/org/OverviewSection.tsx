"use client";

import { Alert, Card, Col, Descriptions, Grid, Row, Tag, theme, Typography } from "antd";
import Link from "next/link";
import { dataHora, mascararCnpj } from "@/lib/org/formato";
import type { Cobranca, EstadoDaOrg } from "@/lib/org/tipos";
import { useRecurso } from "@/lib/org/cliente";
import { hrefDaOrg, ROTULO_DO_TIPO } from "./secoes";
import { SeloDeVerificacao } from "./SeloDeVerificacao";

type Atalho = { titulo: string; descricao: string; href: string };

const ATALHOS_DO_PRESTADOR: Atalho[] = [
  { titulo: "Validar lote", descricao: "Achados do XML antes do envio, grátis.", href: "/playground" },
  { titulo: "Recurso de glosa", descricao: "Peça de recurso a partir do demonstrativo.", href: "/recurso" },
  { titulo: "Extrator", descricao: "Guia SP/SADT a partir de PDF ou imagem.", href: "/extrator" },
];

const atalhosDaOperadora = (orgId: string): Atalho[] => [
  { titulo: "Análise de contas", descricao: "Indícios por guia para a Auditoria decidir.", href: "/analise-contas" },
  { titulo: "Autorização", descricao: "Parecer proposto; a negativa é sempre humana.", href: "/autorizacao" },
  { titulo: "Regras de envio", descricao: "Cadastre e teste as regras com o assistente.", href: hrefDaOrg(orgId, "visao", true) },
];

export function OverviewSection({ org }: { org: EstadoDaOrg }) {
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const cobranca = useRecurso<Cobranca>(org.is_admin || org.my_areas.includes("finance") ? `org/${org.id}/billing/` : null);
  const operadora = org.type === "pay";
  const atalhos = operadora ? atalhosDaOperadora(org.id) : ATALHOS_DO_PRESTADOR;
  const rotulos = new Map(org.available_areas.map((area) => [area.value, area.label]));
  const aceite = org.terms.accepted
    ? `Versão ${org.terms.version}${org.terms.accepted_by ? `, aceitos por ${org.terms.accepted_by}` : ""} em ${dataHora(org.terms.accepted_at)}`
    : "Não aceitos";

  return (
    <>
      {!cobranca.carregando && !cobranca.erro && cobranca.dados && cobranca.dados.enabled !== false && !cobranca.dados.payment_method_active && (
        <Alert type="info" showIcon title={<>Nenhum cartão cadastrado. <Link href={hrefDaOrg(org.id, "cobranca")}>Configurar cobrança</Link></>} />
      )}
      <Row gutter={[token.margin, token.margin]}>
        {atalhos.map((atalho) => (
          <Col key={atalho.titulo} xs={24} md={8}>
            <Link href={atalho.href} style={{ display: "block", height: "100%", textDecoration: "none" }}>
              <Card hoverable style={{ height: "100%" }}>
                <Typography.Text strong style={{ display: "block" }}>{atalho.titulo}</Typography.Text>
                <Typography.Text type="secondary">{atalho.descricao}</Typography.Text>
              </Card>
            </Link>
          </Col>
        ))}
      </Row>
      <Card title="Dados da organização">
        <Descriptions
          bordered
          column={1}
          layout={screens.md ? "horizontal" : "vertical"}
          items={[
            { key: "nome", label: "Nome", children: org.name },
            {
              key: "tipo",
              label: "Tipo",
              children: [ROTULO_DO_TIPO[org.type] ?? org.type_display, org.subtype_display].filter((rotulo, i, lista) => rotulo && lista.indexOf(rotulo) === i).join(" · "),
            },
            {
              key: "cnpj",
              label: "CNPJ",
              children: (
                <>
                  <Typography.Text code>{mascararCnpj(org.cnpj)}</Typography.Text>{" "}
                  <SeloDeVerificacao org={org} />
                </>
              ),
            },
            operadora
              ? { key: "ans", label: "Registro ANS", children: org.registro_ans || "—" }
              : { key: "cnes", label: "CNES", children: org.cnes || <Link href={hrefDaOrg(org.id, "tiss")}>Escolher unidade</Link> },
            { key: "termos", label: "Termos", children: aceite },
            {
              key: "areas",
              label: "Minhas Áreas",
              children: org.my_areas.length
                ? org.my_areas.map((area) => <Tag key={area}>{rotulos.get(area) ?? area}</Tag>)
                : "Nenhuma",
            },
          ]}
        />
      </Card>
    </>
  );
}
