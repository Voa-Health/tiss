import type { FalaDoHistorico } from "./protocolo";

function objeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

/** As falas da cadeia ativa da conversa, na ordem dela; `null` se a resposta não é uma lista de mensagens. */
export function lerHistorico(corpo: unknown): FalaDoHistorico[] | null {
  if (!Array.isArray(corpo)) return null;
  const falas: FalaDoHistorico[] = [];
  for (const linha of corpo) {
    if (!objeto(linha) || (linha.role !== "human" && linha.role !== "ai")) continue;
    const texto = linha.content ?? "";
    if (typeof texto !== "string") return null;
    if (texto.trim()) falas.push({ papel: linha.role === "ai" ? "analista" : "pessoa", texto });
  }
  return falas;
}
