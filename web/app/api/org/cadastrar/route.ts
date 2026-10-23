import { NextResponse, type NextRequest } from "next/server";
import { postarSemToken } from "@/lib/org/backend";
import { corpoDoCadastro, falhaDoCadastro, lerCadastro } from "@/lib/org/cadastro";
import { gravarNome, mesmaOrigem } from "@/lib/org/credencial";
import { cabecalhosDoCliente } from "@/lib/org/ip";

export const dynamic = "force-dynamic";

export async function POST(pedido: NextRequest) {
  if (!mesmaOrigem(pedido)) return NextResponse.json({ detail: "Origem recusada." }, { status: 403 });
  const cadastro = lerCadastro(await pedido.json().catch(() => null));
  if (!cadastro) {
    return NextResponse.json({ detail: "Informe nome, e-mail e senha e aceite os termos." }, { status: 400 });
  }

  const { status, corpo } = await postarSemToken("/auth/registration/", corpoDoCadastro(cadastro), {
    ...cabecalhosDoCliente(pedido.headers),
    "accept-language": "pt-BR",
  });
  if (status === 429) {
    return NextResponse.json({ detail: "Muitos cadastros em pouco tempo. Espere um minuto e tente de novo." }, { status });
  }
  if (status >= 500) return NextResponse.json(corpo, { status });
  if (status >= 300) return NextResponse.json(falhaDoCadastro(corpo), { status: 400 });
  const resposta = NextResponse.json({ email: cadastro.email }, { status: 201 });
  gravarNome(resposta, cadastro.nome);
  return resposta;
}
