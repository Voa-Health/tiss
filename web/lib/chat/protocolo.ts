export type Envelope = {
  event_type?: string;
  event_id?: string | null;
  checkpoint_id?: string | null;
  data?: unknown;
};

export type FalaDoHistorico = { papel: "pessoa" | "analista"; texto: string };

export type AprovacaoPendente = {
  correlation_id: string;
  kind: string;
  resource: string;
  action: string;
  scope: string;
  label: string;
  schema: Record<string, unknown>;
  values: Record<string, unknown>;
};

export type QuadroDeResolucao = {
  type: "hitl-resolve";
  payload: {
    chat_id: string;
    correlation_id: string;
    approved: boolean;
    reason?: string;
  };
};

const EVENTOS_TRATADOS = new Set([
  "response",
  "custom:tool-call-start",
  "custom:tool-call-end",
  "custom:turn-finalized",
  "error",
  "run-accepted",
  "stream-start",
  "stream-end",
  "reattach-ack",
  "keepalive",
  "pong",
  "authenticated",
  "action:create-chat-messages",
  "custom:hitl-pending",
  "custom:hitl-resolved",
]);

function objeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

export function analisarEnvelope(valor: unknown): Envelope | null {
  if (!objeto(valor) || typeof valor.event_type !== "string") return null;
  return valor as Envelope;
}

export function chaveDoEvento(envelope: Envelope): string {
  const tipo = envelope.event_type ?? "";
  if (tipo === "custom" || tipo === "action") {
    const dados = objeto(envelope.data) ? envelope.data : {};
    return `${tipo}:${typeof dados.type === "string" ? dados.type : "?"}`;
  }
  return tipo;
}

export function eventoTratado(envelope: Envelope): boolean {
  return EVENTOS_TRATADOS.has(chaveDoEvento(envelope));
}

export function conteudoDoEvento(envelope: Envelope): Record<string, unknown> {
  const dados = objeto(envelope.data) ? envelope.data : {};
  return objeto(dados.content) ? dados.content : {};
}

export function lerAprovacaoPendente(envelope: Envelope): AprovacaoPendente | null {
  if (chaveDoEvento(envelope) !== "custom:hitl-pending") return null;
  const conteudo = conteudoDoEvento(envelope);
  if (
    typeof conteudo.correlation_id !== "string" ||
    typeof conteudo.resource !== "string" ||
    typeof conteudo.action !== "string" ||
    typeof conteudo.label !== "string" ||
    !objeto(conteudo.values)
  ) return null;
  return {
    correlation_id: conteudo.correlation_id,
    kind: typeof conteudo.kind === "string" ? conteudo.kind : "",
    resource: conteudo.resource,
    action: conteudo.action,
    scope: typeof conteudo.scope === "string" ? conteudo.scope : "",
    label: conteudo.label,
    schema: objeto(conteudo.schema) ? conteudo.schema : {},
    values: conteudo.values,
  };
}

export function lerAprovacaoResolvida(envelope: Envelope): { correlation_id: string; status: string } | null {
  if (chaveDoEvento(envelope) !== "custom:hitl-resolved") return null;
  const conteudo = conteudoDoEvento(envelope);
  if (typeof conteudo.correlation_id !== "string") return null;
  return {
    correlation_id: conteudo.correlation_id,
    status: typeof conteudo.status === "string" ? conteudo.status : "",
  };
}

export function textoDaResposta(envelope: Envelope): string {
  if (typeof envelope.data === "string") return envelope.data;
  if (!objeto(envelope.data)) return "";
  for (const campo of ["content", "text", "delta"]) {
    if (typeof envelope.data[campo] === "string") return envelope.data[campo] as string;
  }
  return "";
}

export function quadroDeEnvio(chatId: string, texto: string, perfil: string) {
  return {
    type: "send" as const,
    payload: { chat_id: chatId, message: texto, profile: perfil },
  };
}

export function quadroDeResolucao(
  chatId: string,
  aprovacao: AprovacaoPendente,
  aprovada: boolean,
  motivo?: string,
): QuadroDeResolucao {
  return {
    type: "hitl-resolve",
    payload: {
      chat_id: chatId,
      correlation_id: aprovacao.correlation_id,
      approved: aprovada,
      ...(motivo?.trim() ? { reason: motivo.trim() } : {}),
    },
  };
}
