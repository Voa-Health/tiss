export const INDICADORES = [
  { chave: "glosa_inicial", rotulo: "Glosa inicial", unidade: "%" },
  { chave: "glosa_final", rotulo: "Glosa final", unidade: "%" },
  { chave: "tempo_medio_pagamento", rotulo: "Tempo médio de pagamento", unidade: "dias" },
  { chave: "guias_sem_retorno", rotulo: "Guias sem retorno", unidade: "%" },
  { chave: "valor_guias_sem_retorno", rotulo: "Valor de guias sem retorno", unidade: "%" },
] as const;

export const FONTE_CADOP = "https://dados.gov.br/dados/conjuntos-dados/operadoras-de-planos-de-saude-ativas";

export type Operadora = {
  registro_ans: string;
  razao_social: string;
  nome_fantasia: string;
  modalidade: string;
  cidade: string;
  uf: string;
};

export type Semestre = { periodo: string; valores: (number | null)[]; inconsistentes: string[] };

export type FontePainel = { titulo: string; url: string; licenca: string; atualizado_em: string };

export function formatValor(valor: number | null): string {
  return valor === null ? "—" : valor.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
}

export function descricaoOperadora(operadora: Operadora, serie: Semestre[]): string {
  const nome = `${operadora.razao_social} (registro ANS ${operadora.registro_ans})`;
  if (!serie.length) {
    return `${nome}: cadastro na ANS, ${operadora.modalidade}, ${operadora.cidade}/${operadora.uf}.`;
  }
  const periodo = `${serie[0].periodo} a ${serie[serie.length - 1].periodo}`;
  return `${nome}: glosa, tempo médio de pagamento e guias sem retorno por semestre, ${periodo}, segundo a ANS.`;
}
