import type { NextRequest, NextResponse } from "next/server";

/** Par de tokens Voa guardado no cookie httpOnly; o navegador nunca o lê. */
export type ParDeTokens = { access: string; refresh: string };

export const COOKIE_DA_ORG = "voa_tiss_org";
const VALIDADE_S = 7 * 24 * 60 * 60;

export function urlDoBackend(): string | null {
  const valor = process.env.VOA_BACKEND_URL?.trim().replace(/\/+$/, "");
  return valor || null;
}

export function lerPar(valor: string | undefined): ParDeTokens | null {
  if (!valor) return null;
  try {
    const par = JSON.parse(Buffer.from(valor, "base64url").toString("utf8")) as Partial<ParDeTokens>;
    return typeof par.access === "string" && typeof par.refresh === "string" && par.access && par.refresh
      ? { access: par.access, refresh: par.refresh }
      : null;
  } catch {
    return null;
  }
}

export function parDoPedido(pedido: NextRequest): ParDeTokens | null {
  return lerPar(pedido.cookies.get(COOKIE_DA_ORG)?.value);
}

export function gravarPar(resposta: NextResponse, par: ParDeTokens): void {
  resposta.cookies.set(COOKIE_DA_ORG, Buffer.from(JSON.stringify(par)).toString("base64url"), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: VALIDADE_S,
  });
}

export function apagarPar(resposta: NextResponse): void {
  resposta.cookies.delete(COOKIE_DA_ORG);
}

/** O cadastro não guarda o nome; ele vai ao perfil na confirmação do e-mail. */
export const COOKIE_DO_NOME = "voa_tiss_nome";

export function gravarNome(resposta: NextResponse, nome: string): void {
  resposta.cookies.set(COOKIE_DO_NOME, Buffer.from(nome).toString("base64url"), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: VALIDADE_S,
  });
}

export function lerNome(pedido: NextRequest): string {
  const valor = pedido.cookies.get(COOKIE_DO_NOME)?.value;
  if (!valor) return "";
  try {
    return Buffer.from(valor, "base64url").toString("utf8").trim().slice(0, 255);
  } catch {
    return "";
  }
}

/** Pedidos que mudam estado só valem vindos desta mesma origem. */
export function mesmaOrigem(pedido: NextRequest): boolean {
  const origem = pedido.headers.get("origin");
  return !origem || origem === pedido.nextUrl.origin;
}
