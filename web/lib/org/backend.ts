import { urlDoBackend, type ParDeTokens } from "./credencial.ts";

export type RespostaDoBackend = {
  status: number;
  corpo: unknown;
  /** Par renovado no caminho, ou `null` se a renovação falhou. */
  par: ParDeTokens | null | undefined;
  /** Corpo em `text/event-stream`, repassado sem ler. */
  fluxo?: ReadableStream<Uint8Array>;
};

async function lerCorpo(resposta: Response): Promise<unknown> {
  if (resposta.status === 204) return null;
  const texto = await resposta.text();
  if (!texto) return null;
  try {
    return JSON.parse(texto);
  } catch {
    return { detail: "Resposta inválida do servidor." };
  }
}

/** `extras` leva os cabeçalhos do navegador (IP) ao backend. */
export async function postarSemToken(
  caminho: string,
  corpo: unknown,
  extras: Record<string, string> = {},
): Promise<{ status: number; corpo: unknown }> {
  const base = urlDoBackend();
  if (!base) return { status: 503, corpo: { detail: "Backend não configurado." } };
  try {
    const resposta = await fetch(`${base}${caminho}`, {
      method: "POST",
      headers: { ...extras, "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify(corpo),
      cache: "no-store",
    });
    return { status: resposta.status, corpo: await lerCorpo(resposta) };
  } catch {
    return { status: 502, corpo: { detail: "O servidor não respondeu. Tente de novo." } };
  }
}

/** `/oauth/token` gira a renovação: a anterior deixa de valer. */
export async function renovar(par: ParDeTokens, extras: Record<string, string> = {}): Promise<ParDeTokens | null> {
  const base = urlDoBackend();
  if (!base) return null;
  let resposta: Response;
  try {
    resposta = await fetch(`${base}/oauth/token`, {
      method: "POST",
      headers: { ...extras, "content-type": "application/x-www-form-urlencoded", accept: "application/json" },
      body: new URLSearchParams({ grant_type: "refresh_token", client_id: "voa-saas", refresh_token: par.refresh }).toString(),
      cache: "no-store",
    });
  } catch {
    return null;
  }
  const corpo = await lerCorpo(resposta);
  if (resposta.status !== 200 || typeof corpo !== "object" || corpo === null) return null;
  const { access_token: access, refresh_token: refresh } = corpo as { access_token?: unknown; refresh_token?: unknown };
  if (typeof access !== "string" || !access || typeof refresh !== "string" || !refresh) return null;
  return { access, refresh };
}

/** Chama o backend e renova o par uma vez se o acesso venceu. */
export async function chamarBackend(
  par: ParDeTokens,
  caminho: string,
  init: { method: string; body?: string; cabecalhos?: Record<string, string>; signal?: AbortSignal },
  extras: Record<string, string> = {},
): Promise<RespostaDoBackend> {
  const base = urlDoBackend();
  if (!base) return { status: 503, corpo: { detail: "Backend não configurado." }, par: undefined };
  const enviar = async (access: string) =>
    fetch(`${base}${caminho}`, {
      method: init.method,
      headers: {
        ...extras,
        accept: "application/json",
        ...init.cabecalhos,
        authorization: `Bearer ${access}`,
        ...(init.body !== undefined ? { "content-type": "application/json" } : {}),
      },
      body: init.body,
      cache: "no-store",
      signal: init.signal,
    });
  let novoPar: ParDeTokens | null | undefined;
  try {
    let resposta = await enviar(par.access);
    if (resposta.status === 401) {
      novoPar = await renovar(par, extras);
      if (!novoPar) return { status: 401, corpo: { detail: "Entre novamente." }, par: null };
      resposta = await enviar(novoPar.access);
    }
    if (resposta.ok && resposta.body && resposta.headers.get("content-type")?.includes("text/event-stream")) {
      return { status: resposta.status, corpo: null, par: novoPar, fluxo: resposta.body };
    }
    return { status: resposta.status, corpo: await lerCorpo(resposta), par: novoPar };
  } catch {
    // A renovação já gastou o refresh anterior; o par novo precisa voltar.
    return { status: 502, corpo: { detail: "O servidor não respondeu. Tente de novo." }, par: novoPar };
  }
}
