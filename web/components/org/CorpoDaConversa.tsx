"use client";

import { CheckOutlined, CloseOutlined, SendOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Flex, Input, List, Space, Spin, Tag, Typography, theme } from "antd";
import { useState } from "react";
import type { AprovacaoPendente, FalaDoHistorico } from "@/lib/chat/protocolo";

type Fala = FalaDoHistorico & { id: string };

function valoresComoLista(valor: unknown): string[] {
  return Array.isArray(valor) ? valor.filter((item): item is string => typeof item === "string") : [];
}

function idsDasRegras(valor: unknown): string[] {
  if (!Array.isArray(valor)) return [];
  return valor.map((item) => {
    if (typeof item !== "object" || item === null) return "";
    if ("id" in item && typeof item.id === "string") return item.id;
    return "";
  }).filter(Boolean);
}

function idsDasAlteracoes(valor: unknown): string[] {
  if (!Array.isArray(valor)) return [];
  return valor.map((item) => {
    if (typeof item !== "object" || item === null) return "";
    if ("id" in item && typeof item.id === "string") return item.id;
    return "";
  }).filter(Boolean);
}

function CartaoDeAprovacao({
  aprovacao,
  carregando,
  podeDecidir,
  aoResolver,
}: {
  aprovacao: AprovacaoPendente;
  carregando: boolean;
  podeDecidir: boolean;
  aoResolver: (aprovada: boolean, motivo?: string) => void;
}) {
  const { token } = theme.useToken();
  const [motivo, setMotivo] = useState("");
  const validacao = aprovacao.values.validation;
  const validacaoObjeto = typeof validacao === "object" && validacao !== null ? validacao as Record<string, unknown> : {};
  const erros = valoresComoLista(validacaoObjeto.errors);
  const semFonte = valoresComoLista(validacaoObjeto.rules_without_source);
  const diferenca = typeof aprovacao.values.diff === "object" && aprovacao.values.diff !== null
    ? aprovacao.values.diff as Record<string, unknown>
    : {};
  const adicionadas = idsDasRegras(diferenca.added);
  const removidas = idsDasRegras(diferenca.removed);
  const alteradas = idsDasAlteracoes(diferenca.changed);

  return (
    <Card
      size="small"
      title={aprovacao.label}
      style={{ borderColor: token.colorWarningBorder }}
      extra={<Tag color="gold">Decisão humana</Tag>}
    >
      <Flex vertical gap={token.marginSM}>
        <Typography.Text type="secondary">{aprovacao.resource} · {aprovacao.action}</Typography.Text>
        {erros.length > 0 && (
          <Alert
            type="error"
            showIcon
            title="Validação"
            description={<List size="small" dataSource={erros} renderItem={(erro) => <List.Item>{erro}</List.Item>} />}
          />
        )}
        {semFonte.length > 0 && (
          <Alert type="warning" showIcon title={`Regras sem fonte: ${semFonte.join(", ")}`} />
        )}
        <div>
          <Typography.Text strong>Diferenças</Typography.Text>
          <List
            size="small"
            dataSource={[
              `Adicionadas (${adicionadas.length}): ${adicionadas.join(", ") || "—"}`,
              `Removidas (${removidas.length}): ${removidas.join(", ") || "—"}`,
              `Alteradas (${alteradas.length}): ${alteradas.join(", ") || "—"}`,
            ]}
            renderItem={(linha) => <List.Item>{linha}</List.Item>}
          />
        </div>
        {podeDecidir ? (
          <>
            <Input.TextArea
              aria-label="Motivo da recusa"
              placeholder="Motivo da recusa (opcional)"
              rows={2}
              value={motivo}
              onChange={(event) => setMotivo(event.target.value)}
            />
            <Space wrap>
              <Button
                type="primary"
                icon={<CheckOutlined />}
                loading={carregando}
                onClick={() => aoResolver(true)}
              >
                Aprovar
              </Button>
              <Button
                danger
                icon={<CloseOutlined />}
                loading={carregando}
                onClick={() => aoResolver(false, motivo)}
              >
                Recusar
              </Button>
            </Space>
          </>
        ) : (
          <Alert type="warning" showIcon title="Só a Área Auditoria decide." />
        )}
      </Flex>
    </Card>
  );
}

export function CorpoDaConversa({
  falas,
  resposta,
  aprovacao,
  erro,
  atividade,
  podeDecidir,
  ignorados,
  conectada,
  trabalhando,
  carregandoDecisao,
  aoEnviar,
  aoResolver,
  aoReconectar,
}: {
  falas: Fala[];
  resposta: string;
  aprovacao: AprovacaoPendente | null;
  erro: string | null;
  atividade: string | null;
  podeDecidir: boolean;
  ignorados: string[];
  conectada: boolean;
  trabalhando: boolean;
  carregandoDecisao: boolean;
  aoEnviar: (texto: string) => void;
  aoResolver: (aprovacao: AprovacaoPendente, aprovada: boolean, motivo?: string) => void;
  aoReconectar: () => void;
}) {
  const { token } = theme.useToken();
  const [texto, setTexto] = useState("");
  const pronto = texto.trim().length > 0 && conectada && !trabalhando;

  function enviar() {
    const mensagem = texto.trim();
    if (!mensagem || !conectada || trabalhando) return;
    aoEnviar(mensagem);
    setTexto("");
  }

  return (
    <Flex vertical gap={token.margin} style={{ minHeight: 0, flex: 1 }}>
      {!conectada && (
        <Alert
          type={erro ? "error" : "info"}
          showIcon
          title={erro ?? "Conectando ao Assistente…"}
          action={erro ? <Button size="small" onClick={aoReconectar}>Tentar novamente</Button> : undefined}
        />
      )}
      {atividade && <Typography.Text type="secondary">{atividade}</Typography.Text>}
      {ignorados.length > 0 && (
        <details>
          <summary>Eventos não utilizados</summary>
          <Typography.Text type="secondary">{ignorados.join(", ")}</Typography.Text>
        </details>
      )}
      <div
        aria-live="polite"
        style={{ display: "flex", flex: 1, minHeight: 180, flexDirection: "column", gap: token.marginSM, overflowY: "auto" }}
      >
        {falas.map((fala) => (
          <Card key={fala.id} size="small" style={{ maxWidth: "95%", alignSelf: fala.papel === "pessoa" ? "flex-end" : "flex-start" }}>
            <Typography.Text strong>{fala.papel === "pessoa" ? "Você" : "Assistente"}</Typography.Text>
            <Typography.Paragraph style={{ whiteSpace: "pre-wrap", margin: `${token.marginXXS}px 0 0` }}>
              {fala.texto}
            </Typography.Paragraph>
          </Card>
        ))}
        {resposta && (
          <Card size="small" style={{ maxWidth: "95%", alignSelf: "flex-start" }}>
            <Typography.Text strong>Assistente</Typography.Text>
            <Typography.Paragraph style={{ whiteSpace: "pre-wrap", margin: `${token.marginXXS}px 0 0` }}>
              {resposta}
            </Typography.Paragraph>
          </Card>
        )}
        {trabalhando && !resposta && (
          <Typography.Text type="secondary"><Spin size="small" /> Preparando resposta…</Typography.Text>
        )}
        {aprovacao && (
          <CartaoDeAprovacao
            aprovacao={aprovacao}
            carregando={carregandoDecisao}
            podeDecidir={podeDecidir}
            aoResolver={(aprovada, motivo) => aoResolver(aprovacao, aprovada, motivo)}
          />
        )}
      </div>
      <Flex gap={token.marginXS} align="flex-end">
        <Input.TextArea
          aria-label="Mensagem para o Assistente"
          placeholder="Descreva a alteração nas regras"
          autoSize={{ minRows: 2, maxRows: 5 }}
          value={texto}
          disabled={!conectada || trabalhando}
          onChange={(event) => setTexto(event.target.value)}
          onPressEnter={(event) => {
            if (!event.shiftKey) {
              event.preventDefault();
              enviar();
            }
          }}
        />
        <Button
          type="primary"
          aria-label="Enviar mensagem"
          icon={<SendOutlined />}
          disabled={!pronto}
          onClick={enviar}
        />
      </Flex>
      <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
        O Assistente propõe; a Auditoria decide. Publicar é sempre uma ação humana da Administração.
      </Typography.Text>
    </Flex>
  );
}
