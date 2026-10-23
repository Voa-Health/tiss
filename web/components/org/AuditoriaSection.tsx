"use client";

import { Alert, App, Button, Card, Empty, Flex, Input, List, Skeleton, Space, Tag, Typography, theme } from "antd";
import { useState } from "react";
import { brl, dataHora } from "@/lib/org/formato";
import { justificativaValida } from "@/lib/org/regras";
import { pedir, useRecurso } from "@/lib/org/cliente";
import type { EstadoDaOrg } from "@/lib/org/tipos";
import type { ItemDeAuditoria, ListaDeAuditoria } from "@/lib/org/tiss";

function prestador(item: ItemDeAuditoria): string {
  if (typeof item.prestador === "string") return item.prestador || "Prestador não informado";
  return String(item.prestador?.nome ?? item.prestador?.razao_social ?? "Prestador não informado");
}

export function AuditoriaSection({ org }: { org: EstadoDaOrg }) {
  const { token } = theme.useToken();
  const { message } = App.useApp();
  const lista = useRecurso<ListaDeAuditoria>("tiss/org/audit/?status=all");
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [justificativa, setJustificativa] = useState("");
  const itens = lista.dados?.items ?? [];
  const escolhido = itens.find((item) => item.id === selecionado) ?? itens.find((item) => item.status === "open") ?? itens[0] ?? null;
  const detalhe = useRecurso<ItemDeAuditoria>(escolhido ? `tiss/org/audit/${escolhido.id}/` : null);
  const item = detalhe.dados ?? escolhido;
  const podeDecidir = org.my_areas.includes("auditoria");

  async function decidir(decisao: "approve" | "reject") {
    if (!item || !justificativaValida(justificativa)) {
      message.error("Informe uma justificativa com pelo menos 10 caracteres.");
      return;
    }
    try {
      await pedir(`tiss/org/audit/${item.id}/${decisao}/`, {
        method: "POST",
        body: { justificativa: justificativa.trim() },
      });
      message.success(decisao === "approve" ? "Pendência aprovada." : "Pendência rejeitada.");
      setJustificativa("");
      lista.recarregar();
      detalhe.recarregar();
    } catch (erro) {
      message.error(erro instanceof Error ? erro.message : "Não foi possível registrar a decisão.");
    }
  }

  if (lista.carregando) return <Skeleton active />;
  if (lista.erro) return <Alert type="error" showIcon title="Não foi possível carregar a fila." description={lista.erro.message} />;

  return (
    <Flex vertical gap={token.margin}>
      <Alert
        type="info"
        showIcon
        title="O agente pode propor; a decisão é sempre da Área Auditoria."
      />
      {(org.is_admin || org.my_areas.includes("administration")) && !podeDecidir && (
        <Alert type="warning" showIcon title="Só a Área Auditoria decide." />
      )}
      {itens.length === 0 ? (
        <Card><Empty description="Nenhuma pendência de Auditoria." /></Card>
      ) : (
        <Flex vertical gap={token.margin}>
          <Card title="Fila de Auditoria" size="small">
            <List
              dataSource={itens}
              renderItem={(linha) => (
                <List.Item
                  key={linha.id}
                  onClick={() => {
                    setSelecionado(linha.id);
                    setJustificativa("");
                  }}
                  style={{ cursor: "pointer", background: linha.id === item?.id ? token.colorFillTertiary : undefined }}
                >
                  <List.Item.Meta
                    title={<Typography.Text strong>Guia {linha.numero_guia || "sem número"}</Typography.Text>}
                    description={`${prestador(linha)} · ${linha.kind_display || linha.tipo || "Análise"}`}
                  />
                  <Tag color={linha.status === "open" ? "processing" : undefined}>
                    {linha.status === "open" ? "Em aberto" : "Resolvida"}
                  </Tag>
                </List.Item>
              )}
            />
          </Card>
          {item && (
            <Card title={`Detalhe da guia ${item.numero_guia || "sem número"}`} loading={detalhe.carregando}>
              <Flex vertical gap={token.margin}>
                <Typography.Text type="secondary">
                  {item.kind_display || item.tipo || "Análise"} · {prestador(item)}
                </Typography.Text>
                <Typography.Paragraph style={{ margin: 0 }}>{item.reason || "Motivo não informado."}</Typography.Paragraph>
                {(item.itens ?? []).length > 0 && (
                  <List
                    size="small"
                    dataSource={item.itens}
                    renderItem={(linha) => (
                      <List.Item>
                        <Flex vertical style={{ width: "100%" }}>
                          <Typography.Text strong>{linha.codigo_glosa || "Código não informado"}</Typography.Text>
                          <Typography.Text>{linha.motivo || "Motivo não informado"}</Typography.Text>
                          {linha.valor !== undefined && linha.valor !== null && (
                            <Typography.Text type="secondary">{brl(linha.valor)}</Typography.Text>
                          )}
                        </Flex>
                      </List.Item>
                    )}
                  />
                )}
                <Typography.Text type="secondary">
                  Aberta em {dataHora(item.opened_at)}
                </Typography.Text>
                {item.status === "open" && podeDecidir ? (
                  <Flex vertical gap={token.marginSM}>
                    <Input.TextArea
                      aria-label="Justificativa da decisão"
                      placeholder="Justificativa (mínimo de 10 caracteres)"
                      rows={3}
                      value={justificativa}
                      onChange={(event) => setJustificativa(event.target.value)}
                    />
                    <Space wrap>
                      <Button
                        type="primary"
                        disabled={!justificativaValida(justificativa)}
                        onClick={() => void decidir("approve")}
                      >
                        Aprovar
                      </Button>
                      <Button
                        danger
                        disabled={!justificativaValida(justificativa)}
                        onClick={() => void decidir("reject")}
                      >
                        Recusar
                      </Button>
                    </Space>
                  </Flex>
                ) : null}
              </Flex>
            </Card>
          )}
        </Flex>
      )}
    </Flex>
  );
}
