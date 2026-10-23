export type StatusDaBusca = "resolvida" | "ambigua" | "ausente" | "fora-do-registro" | "indisponivel";

export type Unidade = { cnes: string; nome: string; municipio: string };

export type RespostaDaBusca = { status: StatusDaBusca; nome_oficial: string; unidades: Unidade[] };

export type ChaveDaBusca = { campo: "cnpj" | "registro_ans"; valor: string };

export type Situacao = {
  status: StatusDaBusca;
  nomeOficial: string;
  unidades: Unidade[];
  alerta: "success" | "info" | "warning";
  mensagem: string;
};

const STATUS: readonly StatusDaBusca[] = ["resolvida", "ambigua", "ausente", "fora-do-registro", "indisponivel"];

const texto = (valor: unknown) => (typeof valor === "string" ? valor.trim() : "");

export const soDigitos = (valor: string | undefined) => (valor ?? "").replace(/\D/g, "");

/** Operadora busca pelo Registro ANS; as demais, pelo CNPJ completo. */
export function chaveDaBusca(tipo: string | undefined, cnpj: string | undefined, registroAns: string | undefined): ChaveDaBusca | null {
  if (tipo === "pay") {
    const valor = soDigitos(registroAns);
    return valor.length === 6 ? { campo: "registro_ans", valor } : null;
  }
  const valor = soDigitos(cnpj);
  return valor.length === 14 ? { campo: "cnpj", valor } : null;
}

export function caminhoDaBusca({ campo, valor }: ChaveDaBusca): string {
  return `tiss/organizations/lookup/?${new URLSearchParams({ [campo]: valor })}`;
}

/** Resposta fora do contrato vira `indisponivel`: a busca nunca trava o cadastro. */
export function lerResposta(corpo: unknown): RespostaDaBusca {
  const dados = typeof corpo === "object" && corpo !== null ? (corpo as Record<string, unknown>) : {};
  const status = STATUS.find((item) => item === dados.status) ?? "indisponivel";
  const unidades = status === "ambigua" && Array.isArray(dados.unidades)
    ? dados.unidades
      .map((item) => (typeof item === "object" && item !== null ? (item as Record<string, unknown>) : {}))
      .map((item) => ({ cnes: texto(item.cnes), nome: texto(item.nome), municipio: texto(item.municipio) }))
      .filter((item) => item.cnes)
    : [];
  return { status, nome_oficial: texto(dados.nome_oficial), unidades };
}

export function situacaoDaBusca(resposta: RespostaDaBusca, campo: ChaveDaBusca["campo"]): Situacao {
  const base = { status: resposta.status, nomeOficial: resposta.nome_oficial, unidades: resposta.unidades };
  const chave = campo === "registro_ans" ? "Registro ANS" : "CNPJ";
  const registro = campo === "registro_ans" ? "registro da ANS" : "CNES";
  switch (resposta.status) {
    case "resolvida":
      return {
        ...base,
        alerta: "success",
        mensagem: resposta.nome_oficial
          ? `Encontramos ${resposta.nome_oficial} no ${registro}. A organização entra como verificada.`
          : `Encontramos este ${chave} no ${registro}. A organização entra como verificada.`,
      };
    case "ambigua":
      return {
        ...base,
        alerta: "info",
        mensagem: `Este ${chave} tem ${resposta.unidades.length} unidades no ${registro}. Escolha a sua para verificar a organização; se pular, ela entra como não verificada e você escolhe depois em Configurações.`,
      };
    case "ausente":
      return {
        ...base,
        alerta: "warning",
        mensagem: `Não achamos este ${chave} no ${registro}. Confira os números; se estiverem certos, siga: a organização entra como não verificada e funciona normalmente.`,
      };
    case "fora-do-registro":
      return {
        ...base,
        alerta: "info",
        mensagem: `Este ${chave} não é do tipo que o ${registro} cadastra. A organização entra como não verificada e funciona normalmente.`,
      };
    default:
      return {
        ...base,
        alerta: "info",
        mensagem: `Não conseguimos consultar o ${registro} agora. Siga com o cadastro; verificamos a organização depois.`,
      };
  }
}

/** Sugere o nome oficial sem apagar o que a pessoa já digitou. */
export function nomeSugerido(atual: string | undefined, resposta: RespostaDaBusca): string | null {
  if (texto(atual) || !resposta.nome_oficial) return null;
  return resposta.status === "resolvida" || resposta.status === "ambigua" ? resposta.nome_oficial : null;
}

export function rotuloDaUnidade(unidade: Unidade): string {
  return [unidade.nome || "Unidade sem nome", unidade.municipio, `CNES ${unidade.cnes}`].filter(Boolean).join(" · ");
}
