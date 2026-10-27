import type { FalaDoHistorico } from "./protocolo";

function objeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

/** Falas da cadeia ativa, em ordem; `null` se a resposta não é uma lista. */
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
