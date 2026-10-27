import type { NextRequest } from "next/server";

export const COOKIE_DA_CONVERSA = "tiss_conversa";
export const VALIDADE_DA_CONVERSA_S = 7 * 24 * 60 * 60;

const ID = /^[\w-]+$/;

export const idValido = (valor: string) => ID.test(valor);

export const perfilDoChat = () => process.env.TISS_CHAT_PROFILE?.trim() || null;

/** A conversa lembrada é por org: o cookie só vale no caminho da org. */
export const caminhoDaConversa = (orgId: string) => `/api/conversa/${orgId}`;

export const chatDaOrg = (orgId: string, chatId: string, resto = "") => `/api/v2/org/${orgId}/chat/${chatId}/${resto}`;

export function cabecalhoDoCursor(pedido: NextRequest): Record<string, string> {
  const cursor = pedido.headers.get("last-event-id");
  return cursor ? { "last-event-id": cursor } : {};
}
