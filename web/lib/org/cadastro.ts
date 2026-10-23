/** Cliente do cadastro: confirma o e-mail no /org e não reserva teste do plano Pro. */
export const CLIENTE_DO_CADASTRO = "tiss-org";
export const CANAL_DO_CADASTRO = "tiss";

export type DadosDoCadastro = { email: string; senha: string; nome: string; aceite: boolean };

const texto = (valor: unknown) => (typeof valor === "string" ? valor : "");

export function lerCadastro(corpo: unknown): DadosDoCadastro | null {
  const dados = typeof corpo === "object" && corpo !== null ? (corpo as Record<string, unknown>) : {};
  const cadastro = {
    email: texto(dados.email).trim().toLowerCase(),
    senha: texto(dados.senha),
    nome: texto(dados.nome).trim().slice(0, 255),
    aceite: dados.aceite === true,
  };
  return cadastro.email && cadastro.senha && cadastro.nome && cadastro.aceite ? cadastro : null;
}

export function corpoDoCadastro({ email, senha }: DadosDoCadastro) {
  return { email, password1: senha, password2: senha, client: CLIENTE_DO_CADASTRO, channel: CANAL_DO_CADASTRO };
}

const MENSAGENS: [RegExp, string][] = [
  [/already registered/i, "Já existe uma conta com este e-mail. Entre com ela ou recupere a senha."],
  [/não foi verificado/i, "Este e-mail já foi cadastrado e falta confirmar. Reenviamos o link se você pedir abaixo."],
  [/too short|muito curta/i, "A senha precisa de pelo menos 8 caracteres."],
  [/too common|muito comum/i, "Essa senha é comum demais. Escolha outra."],
  [/entirely numeric|inteiramente numérica/i, "A senha não pode ter só números."],
  [/too similar|muito parecida/i, "A senha está parecida demais com o e-mail."],
];

function primeira(valor: unknown): string {
  if (typeof valor === "string") return valor;
  if (Array.isArray(valor)) return primeira(valor[0]);
  return "";
}

function traduzir(mensagem: string): string {
  return MENSAGENS.find(([padrao]) => padrao.test(mensagem))?.[1] ?? mensagem;
}

/** Erros do backend nos nomes de campo do formulário do site. */
export function falhaDoCadastro(corpo: unknown): { detail: string; email?: string; senha?: string } {
  const dados = typeof corpo === "object" && corpo !== null ? (corpo as Record<string, unknown>) : {};
  const email = primeira(dados.email);
  const senha = primeira(dados.password1) || primeira(dados.password2) || primeira(dados.non_field_errors);
  const resultado: { detail: string; email?: string; senha?: string } = {
    detail: traduzir(primeira(dados.detail) || email || senha) || "Não foi possível criar a conta. Tente de novo.",
  };
  if (email) resultado.email = traduzir(email);
  if (senha) resultado.senha = traduzir(senha);
  return resultado;
}
