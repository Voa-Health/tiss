import type { FalaDoHistorico } from "./protocolo";

function objeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

export async function carregarHistorico(
  base: string,
  token: string,
  chatId: string,
): Promise<FalaDoHistorico[]> {
  const destino = new URL(`${base.replace(/\/+$/, "")}/api/v1/chat/${encodeURIComponent(chatId)}/messages/`);
  const falas: FalaDoHistorico[] = [];
  let pagina = 1;

  while (true) {
    const url = new URL(destino);
    url.search = new URLSearchParams({
      ordering: "created_at",
      page_size: "100",
      page: String(pagina),
    }).toString();
    const resposta = await fetch(url, {
      headers: { authorization: `Bearer ${token}` },
      cache: "no-store",
      redirect: "error",
    });
    if (!resposta.ok) throw new Error(`Histórico indisponível (HTTP ${resposta.status}).`);
    const dados: unknown = await resposta.json();
    const linhas = Array.isArray(dados) ? dados : objeto(dados) ? dados.results : null;
    if (!Array.isArray(linhas)) throw new Error("Resposta de histórico inválida.");

    for (const linha of linhas) {
      if (!objeto(linha) || (linha.role !== "human" && linha.role !== "ai")) continue;
      const texto = linha.content ?? "";
      if (typeof texto !== "string") throw new Error("Mensagem de histórico inválida.");
      if (texto.trim()) falas.push({ papel: linha.role === "ai" ? "analista" : "pessoa", texto });
    }
    if (Array.isArray(dados)) return falas;
    if (!objeto(dados)) throw new Error("Resposta de histórico inválida.");

    let seguinte: unknown;
    if ("next_page" in dados) {
      seguinte = dados.next_page;
    } else if (dados.next === null) {
      seguinte = null;
    } else if (typeof dados.next === "string") {
      const proxima = new URL(dados.next, destino);
      if (proxima.origin !== destino.origin || proxima.pathname !== destino.pathname) {
        throw new Error("Paginação de histórico inválida.");
      }
      seguinte = Number(proxima.searchParams.get("page"));
    }
    if (seguinte === null) return falas;
    if (typeof seguinte !== "number" || !Number.isSafeInteger(seguinte) || seguinte <= pagina) {
      throw new Error("Paginação de histórico inválida.");
    }
    pagina = seguinte;
  }
}
