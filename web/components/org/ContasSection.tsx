"use client";

import { Alert, Card, Col, Empty, Flex, Row, Skeleton, Tag, Typography, theme } from "antd";
import { brl, dataHora } from "@/lib/org/formato";
import { rotuloDoEstadoDaConta } from "@/lib/org/contas";
import { useRecurso } from "@/lib/org/cliente";
import type { EstadoDaOrg } from "@/lib/org/tipos";
import type { ContaTiss, ListaDeContas } from "@/lib/org/tiss";

function nomeDoPrestador(prestador: Record<string, unknown>): string {
  for (const campo of ["nome", "razao_social", "name"]) {
    const valor = prestador[campo];
    if (typeof valor === "string" && valor) return valor;
  }
  return "Prestador não informado";
}

function valorDaConta(total: ContaTiss["total"]): string {
  if (typeof total === "number" || typeof total === "string") return brl(total);
  if (total && typeof total === "object") {
    const valor = total.value;
    if (typeof valor === "number" || typeof valor === "string") return brl(valor);
  }
  return "Valor não informado";
}

export function ContasSection({ org }: { org: EstadoDaOrg }) {
  const { token } = theme.useToken();
  const permitidas = ["auditoria", "administration", "finance"];
  const podeVer = org.is_admin || org.my_areas.some((area) => permitidas.includes(area));
  const contas = useRecurso<ListaDeContas>(podeVer ? `org/${org.id}/tiss/account/` : null);

  if (!podeVer) {
    return <Alert type="warning" showIcon title="Acesso restrito" description="Contas está disponível para as Áreas Auditoria, Administração e Financeiro." />;
  }
  if (contas.carregando) return <Skeleton active />;
  if (contas.erro) {
    return <Alert type="error" showIcon title="Não foi possível carregar as contas." description={contas.erro.message} />;
  }
  const itens = contas.dados?.results ?? [];

  return (
    <Flex vertical gap={token.margin}>
      <Alert
        type="info"
        showIcon
        title="As decisões registradas aparecem junto ao estado da conta."
      />
      {itens.length === 0 ? (
        <Card><Empty description="Nenhuma conta analisada." /></Card>
      ) : (
        <Row gutter={[token.margin, token.margin]}>
          {itens.map((conta) => {
            const estado = rotuloDoEstadoDaConta(conta);
            const prestador = nomeDoPrestador(conta.prestador ?? {});
            return (
              <Col key={conta.id} xs={24} md={12} xl={8}>
                <Card title={`Guia ${conta.numero_guia || "sem número"}`} size="small" style={{ height: "100%" }}>
                  <Flex vertical gap={token.marginXS}>
                    <Typography.Text strong>{prestador}</Typography.Text>
                    <Typography.Text type="secondary">{conta.kind || "Conta TISS"}</Typography.Text>
                    <Typography.Text>{valorDaConta(conta.total)}</Typography.Text>
                    <Flex wrap gap={token.marginXS} align="center">
                      <Tag color={conta.status === "active" ? "green" : conta.status === "draft" ? "gold" : undefined}>
                        {estado}
                      </Tag>
                      {conta.review_required && <Tag>Revisão humana</Tag>}
                    </Flex>
                    <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                      Atualizada em {dataHora(conta.created)}
                    </Typography.Text>
                  </Flex>
                </Card>
              </Col>
            );
          })}
        </Row>
      )}
    </Flex>
  );
}
