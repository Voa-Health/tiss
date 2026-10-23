"use client";

import { Alert, Button, Card, Flex, Skeleton, Statistic, Table, theme, Typography } from "antd";
import type { TableColumnsType } from "antd";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatLaunchPrice, launchPriceLabel, launchPrices, moduleContent, type ModuleSlug } from "@/lib/modules";
import { FalhaDoPedido, pedir, useRecurso } from "@/lib/org/cliente";
import { brl, dia } from "@/lib/org/formato";
import type { Cobranca, Fatura, Uso } from "@/lib/org/tipos";
import { hrefDaOrg } from "./secoes";

const SITUACOES: Record<string, string> = {
  draft: "Rascunho", open: "Em aberto", paid: "Paga", void: "Cancelada", uncollectible: "Incobrável",
};

export function BillingSection({ podeVer, rotuloFinanceiro }: { podeVer: boolean; rotuloFinanceiro: string }) {
  const { token } = theme.useToken();
  const retorno = useSearchParams().get("setup");
  const cobranca = useRecurso<Cobranca>(podeVer ? "tiss/org/billing/" : null);
  const faturas = useRecurso<Fatura[]>(podeVer ? "tiss/org/billing/invoices/" : null);
  const dias = new Intl.DateTimeFormat("en-US", { timeZone: "America/Sao_Paulo", day: "numeric" }).format(new Date());
  const uso = useRecurso<Uso>(podeVer ? `tiss/org/usage/?days=${dias}` : null);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<FalhaDoPedido | null>(null);
  const erros = [cobranca.erro, faturas.erro, erro];
  const indisponivel = erros.some((item) => item?.status === 503 && item.code === "billing_disabled");

  async function cadastrar() {
    setEnviando(true);
    setErro(null);
    try {
      const dados = await pedir<{ checkout_url: string }>("tiss/org/billing/setup/", { method: "POST" });
      window.location.assign(dados.checkout_url);
    } catch (motivo) {
      setErro(motivo instanceof FalhaDoPedido ? motivo : new FalhaDoPedido(0, "Não foi possível cadastrar o cartão."));
      setEnviando(false);
    }
  }

  if (!podeVer || erros.some((item) => item?.status === 403)) {
    return <Card><EmptyState title="Cobrança restrita" description={`A cobrança é gerenciada pela Administração ou pela Área ${rotuloFinanceiro}.`} /></Card>;
  }

  const cartao = cobranca.dados?.payment_method;
  const colunas: TableColumnsType<Fatura> = [
    { title: "Data", dataIndex: "created", render: (valor: string | null) => valor ? dia(valor) : "—" },
    { title: "Valor", key: "valor", render: (_, item) => {
      const valor = item.total ?? item.amount_due ?? item.amount_paid;
      return valor === null ? "—" : brl(valor);
    } },
    { title: "Status", dataIndex: "status", render: (valor: string | null) => valor ? SITUACOES[valor] ?? "Não informado" : "—" },
    { title: "Fatura", key: "link", render: (_, item) => <Flex gap={token.marginSM}>
      {item.invoice_pdf && <a href={item.invoice_pdf} target="_blank" rel="noopener noreferrer">PDF</a>}
      {item.hosted_invoice_url && <a href={item.hosted_invoice_url} target="_blank" rel="noopener noreferrer">Ver fatura</a>}
      {!item.invoice_pdf && !item.hosted_invoice_url && "—"}
    </Flex> },
  ];

  return <Flex vertical gap={token.marginLG}>
    {retorno === "ok" && <Alert type="success" showIcon title="Cartão recebido; a confirmação pode levar alguns segundos" action={<Button onClick={cobranca.recarregar}>Atualizar</Button>} />}
    {retorno === "cancel" && <Alert type="info" showIcon title="Cadastro cancelado. Nada foi alterado." />}
    {indisponivel ? <Alert type="info" showIcon title="Cobrança ainda não disponível" /> : <Card title="Forma de pagamento">
      <Flex vertical gap={token.margin}>
        {cobranca.carregando ? <Skeleton active /> : cobranca.erro ? <Alert type="error" title={cobranca.erro.message} action={<Button onClick={cobranca.recarregar}>Atualizar</Button>} /> : <Typography.Text>{cartao ? `${cartao.brand} •••• ${cartao.last4} · Validade ${String(cartao.exp_month).padStart(2, "0")}/${cartao.exp_year}` : "Nenhum cartão cadastrado"}</Typography.Text>}
        {erro && <Alert type="error" showIcon title={erro.message} />}
        <div><Button type="primary" loading={enviando} onClick={() => void cadastrar()}>{cartao ? "Trocar cartão" : "Cadastrar cartão"}</Button></div>
      </Flex>
    </Card>}
    <Card>
      {uso.carregando ? <Skeleton active /> : uso.erro ? <Alert type="warning" title="Não foi possível carregar o custo estimado." action={<Button onClick={uso.recarregar}>Atualizar</Button>} /> : <Statistic title="Custo estimado do mês" value={uso.dados ? brl(uso.dados.estimated_total_brl) : "—"} />}
      <Link href={hrefDaOrg("uso")}>Ver detalhes de uso</Link>
    </Card>
    {!indisponivel && <Card title="Faturas">
      {faturas.erro ? <Alert type="error" title={faturas.erro.message} action={<Button onClick={faturas.recarregar}>Atualizar</Button>} /> : <Table rowKey={(item) => item.id ?? String(faturas.dados?.indexOf(item))} columns={colunas} dataSource={faturas.dados ?? []} loading={faturas.carregando} scroll={{ x: 480 }} pagination={{ pageSize: 10 }} locale={{ emptyText: <EmptyState title="Nenhuma fatura" description="As faturas da organização aparecerão aqui." /> }} />}
    </Card>}
    <Card title={launchPriceLabel}>
      <Table rowKey="modulo" pagination={false} columns={[
        { title: "Módulo", dataIndex: "modulo" }, { title: "Preço", dataIndex: "preco" }, { title: "Condições", dataIndex: "nota" },
      ]} scroll={{ x: 600 }} dataSource={(Object.keys(launchPrices) as ModuleSlug[]).map((chave) => ({ modulo: moduleContent[chave].label, preco: formatLaunchPrice(launchPrices[chave]), nota: launchPrices[chave].note ?? "—" }))} />
    </Card>
  </Flex>;
}
