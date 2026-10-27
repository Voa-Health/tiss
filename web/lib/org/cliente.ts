"use client";

import { useCallback, useEffect, useState } from "react";

export class FalhaDoPedido extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly campos: Record<string, string> = {},
    readonly code?: string,
  ) {
    super(message);
  }
}

function primeiraMensagem(valor: unknown): string {
  if (typeof valor === "string") return valor;
  if (Array.isArray(valor)) return primeiraMensagem(valor[0]);
  if (typeof valor === "object" && valor !== null) return primeiraMensagem(Object.values(valor)[0]);
  return "";
}

function falha(status: number, corpo: unknown): FalhaDoPedido {
  const campos: Record<string, string> = {};
  let detalhe = "";
  if (typeof corpo === "object" && corpo !== null) {
    for (const [campo, valor] of Object.entries(corpo)) {
      if (campo === "detail" || campo === "code") continue;
      const mensagem = primeiraMensagem(valor);
      if (mensagem) campos[campo] = mensagem;
    }
    if ("detail" in corpo) detalhe = primeiraMensagem(corpo.detail);
  }
  const mensagem = detalhe || Object.values(campos)[0] || "Não foi possível concluir. Tente de novo.";
  const code = typeof corpo === "object" && corpo !== null && "code" in corpo && typeof corpo.code === "string" ? corpo.code : undefined;
  return new FalhaDoPedido(status, mensagem, campos, code);
}

/** Chama o BFF do painel; o navegador nunca vê o token Voa. */
export async function pedir<T>(caminho: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const destino = caminho.startsWith("/") ? caminho : `/api/org/${caminho.replace(/\/(?=$|\?)/, "")}`;
  const resposta = await fetch(destino, {
    method: init.method ?? "GET",
    headers: init.body !== undefined ? { "content-type": "application/json" } : undefined,
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    cache: "no-store",
  });
  if (resposta.status === 204) return null as T;
  const corpo: unknown = await resposta.json().catch(() => null);
  if (!resposta.ok) throw falha(resposta.status, corpo);
  return corpo as T;
}

export type Recurso<T> = {
  dados: T | null;
  erro: FalhaDoPedido | null;
  carregando: boolean;
  recarregar: () => void;
};

type Resultado<T> = { chave: string; dados: T | null; erro: FalhaDoPedido | null };

export function useRecurso<T>(caminho: string | null): Recurso<T> {
  const [versao, setVersao] = useState(0);
  const [resultado, setResultado] = useState<Resultado<T>>({ chave: "", dados: null, erro: null });
  const chave = caminho ? `${caminho}#${versao}` : "";

  useEffect(() => {
    if (!caminho) return;
    let vivo = true;
    pedir<T>(caminho)
      .then((dados) => vivo && setResultado({ chave, dados, erro: null }))
      .catch((motivo: unknown) => {
        if (!vivo) return;
        const erro = motivo instanceof FalhaDoPedido ? motivo : new FalhaDoPedido(0, "Não foi possível carregar.");
        setResultado((anterior) => ({ chave, dados: anterior.dados, erro }));
      });
    return () => {
      vivo = false;
    };
  }, [caminho, chave]);

  const recarregar = useCallback(() => setVersao((valor) => valor + 1), []);
  const carregando = Boolean(caminho) && resultado.chave !== chave;
  return { dados: resultado.dados, erro: carregando ? null : resultado.erro, carregando, recarregar };
}

/** Recarrega a página: a sessão mudou e os dados em memória ficaram velhos. */
export function abrirDeNovo(caminho = "/org"): void {
  window.location.replace(new URL(caminho, window.location.origin));
}
