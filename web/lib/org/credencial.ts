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

/** Pedidos que mudam estado só valem vindos desta mesma origem. */
export function mesmaOrigem(pedido: NextRequest): boolean {
  const origem = pedido.headers.get("origin");
  return !origem || origem === pedido.nextUrl.origin;
}
