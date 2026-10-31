export type PrestadorDoMapa = { id: string; name: string | null; name_source: "registry" | "cnes" | "claims" | null };
export type LinhaDoMapa = {
  provider: PrestadorDoMapa; month: string | null; code: string;
  glosa: string | null; rule_id: string | null; guias: number; affected_amount: string;
};
export type MapaDeRejeicao = {
  eligible: boolean; enabled: boolean;
  terms: { current_version: string; url: string; version: string; accepted_at: string | null; accepted_by: string | null };
  rows: LinhaDoMapa[]; providers: PrestadorDoMapa[]; rule_ids: (string | null)[]; codes: string[];
};
export type NomeDoPrestador = { provider: string; name: string };
export type CelulaDoMapa = { guias: number; centavos: number };
export type LinhaDaMatriz = { prestador: PrestadorDoMapa; meses: Record<string, CelulaDoMapa>; total: CelulaDoMapa };
export const caminhoDoMapa = (orgId: string) => `org/${orgId}/tiss/rejection-map/`;

export function rotuloDoPrestador(prestador: PrestadorDoMapa): string {
  if (prestador.name) return prestador.name;
  if (prestador.id.startsWith("codigo:")) return `Código ${prestador.id.slice(7)}`;
  if (prestador.id.startsWith("cpf:hmac:")) return `CPF pseudonimizado …${prestador.id.slice(-4)}`;
  const cnpj = prestador.id.slice(5);
  if (prestador.id.startsWith("cnpj:") && /^\d{14}$/.test(cnpj)) {
    return cnpj.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
  }
  return prestador.id;
}

export function matrizDoMapa(linhas: LinhaDoMapa[]) {
  const meses = [...new Set(linhas.map((linha) => linha.month ?? "sem mês"))].sort();
  const prestadores = new Map<string, LinhaDaMatriz>();
  for (const linha of linhas) {
    const atual = prestadores.get(linha.provider.id) ?? {
      prestador: linha.provider, meses: {}, total: { guias: 0, centavos: 0 },
    };
    const mes = linha.month ?? "sem mês";
    const celula = atual.meses[mes] ?? { guias: 0, centavos: 0 };
    const centavos = Math.round(Number(linha.affected_amount) * 100);
    celula.guias += linha.guias;
    celula.centavos += centavos;
    atual.meses[mes] = celula;
    atual.total.guias += linha.guias;
    atual.total.centavos += centavos;
    prestadores.set(linha.provider.id, atual);
  }
  return { meses, linhas: [...prestadores.values()] };
}

function linhasCsv(texto: string): string[][] {
  const linhas: string[][] = [];
  let linha: string[] = [], campo = "", aspas = false;
  for (let i = 0; i < texto.length; i++) {
    const char = texto[i];
    if (char === '"') {
      if (aspas && texto[i + 1] === '"') { campo += '"'; i++; }
      else if (aspas || !campo) aspas = !aspas;
      else throw new Error("CSV inválido.");
    } else if (!aspas && (char === "," || char === "\n")) {
      linha.push(campo); campo = "";
      if (char === "\n") { linhas.push(linha); linha = []; }
    } else if (char !== "\r" || aspas) campo += char;
  }
  if (aspas) throw new Error("CSV com aspas não fechadas.");
  if (campo || linha.length) { linha.push(campo); linhas.push(linha); }
  return linhas.filter((itens) => itens.some((item) => item.trim()));
}

export function lerCadastro(texto: string, json: boolean): NomeDoPrestador[] {
  const conteudo = texto.replace(/^\uFEFF/, "");
  let itens: unknown;
  if (json) itens = JSON.parse(conteudo);
  else {
    const [cabecalho, ...linhas] = linhasCsv(conteudo);
    if (cabecalho?.join(",") !== "provider,name" || linhas.some((linha) => linha.length !== 2)) {
      throw new Error("Use o cabeçalho provider,name e duas colunas.");
    }
    itens = linhas.map(([provider, name]) => ({ provider, name }));
  }
  if (!Array.isArray(itens) || itens.length > 5000) throw new Error("Envie uma lista com até 5000 nomes.");
  return itens.map((item: unknown) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) throw new Error("Cadastro inválido.");
    const campos = item as Record<string, unknown>;
    if (Object.keys(campos).sort().join(",") !== "name,provider" || typeof campos.provider !== "string" ||
        typeof campos.name !== "string" || !campos.name.trim() || campos.name.trim().length > 200) {
      throw new Error("Cada item deve conter apenas prestador e nome (até 200 caracteres).");
    }
    return { provider: campos.provider.trim(), name: campos.name.trim() };
  });
}

export async function identificarPrestador(valor: string, segredo: () => Promise<string>): Promise<string> {
  const id = valor.trim();
  if (/^cpf:hmac:[0-9a-f]{64}$/.test(id)) return id;
  if (id.startsWith("codigo:")) {
    const codigo = id.slice(7).trim();
    if (codigo && codigo.length <= 80) return `codigo:${codigo}`;
    throw new Error("Código de prestador inválido.");
  }
  const documento = id.replace(/^(cnpj|cpf):/i, "");
  if (/^[\d.\-/\s]+$/.test(documento)) {
    const digitos = documento.replace(/\D/g, "");
    if (digitos.length === 14 && !/^cpf:/i.test(id)) return `cnpj:${digitos}`;
    if (digitos.length === 11 && !/^cnpj:/i.test(id)) {
      const encoder = new TextEncoder();
      const chave = await crypto.subtle.importKey("raw", encoder.encode(await segredo()), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
      const assinatura = await crypto.subtle.sign("HMAC", chave, encoder.encode(digitos));
      return `cpf:hmac:${Array.from(new Uint8Array(assinatura), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
    }
  }
  if (!id.includes(":") && /^[\w-]+$/.test(id) && id.length <= 80) return `codigo:${id}`;
  throw new Error("Identificador inválido. Use codigo:…, CNPJ ou CPF.");
}

export async function prepararCadastro(itens: NomeDoPrestador[], segredo: () => Promise<string>) {
  const resultado: NomeDoPrestador[] = [], vistos = new Set<string>();
  let segredoPendente: Promise<string> | undefined;
  for (const item of itens) {
    const prestador = await identificarPrestador(item.provider, () => segredoPendente ??= segredo());
    if (vistos.has(prestador)) throw new Error("Há prestadores repetidos no arquivo.");
    vistos.add(prestador);
    resultado.push({ provider: prestador, name: item.name });
  }
  return resultado;
}
