export type DadosDoLinkOficial = {
  repository: string;
  path: string;
  title: string;
  body: string;
  content: string;
};

export type LinkOficial = {
  url: string;
  titulo: string;
  corpo: string;
  conteudo: string;
  conteudoNoModal: boolean;
};

export function justificativaValida(valor: string): boolean {
  return valor.trim().length >= 10;
}

export function montarLinkOficial(dados: DadosDoLinkOficial, limite = 8_000): LinkOficial {
  if (!/^[\w.-]+\/[\w.-]+$/.test(dados.repository)) throw new Error("Repositório inválido.");
  const base = `https://github.com/${dados.repository}/new/main`;
  const filename = `?filename=${encodeURIComponent(dados.path)}`;
  const urlCompleta = `${base}${filename}&value=${encodeURIComponent(dados.content)}`;
  const conteudoNoModal = urlCompleta.length > limite;
  return {
    url: conteudoNoModal ? `${base}${filename}` : urlCompleta,
    titulo: dados.title,
    corpo: dados.body,
    conteudo: dados.content,
    conteudoNoModal,
  };
}
