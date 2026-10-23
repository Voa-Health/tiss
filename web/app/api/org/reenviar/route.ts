import { NextResponse, type NextRequest } from "next/server";
import { postarSemToken } from "@/lib/org/backend";
import { CLIENTE_DO_CADASTRO } from "@/lib/org/cadastro";
import { mesmaOrigem } from "@/lib/org/credencial";
import { cabecalhosDoCliente } from "@/lib/org/ip";

export const dynamic = "force-dynamic";

export async function POST(pedido: NextRequest) {
  if (!mesmaOrigem(pedido)) return NextResponse.json({ detail: "Origem recusada." }, { status: 403 });
  const dados = (await pedido.json().catch(() => null)) as { email?: unknown } | null;
  const email = typeof dados?.email === "string" ? dados.email.trim().toLowerCase() : "";
  if (!email) return NextResponse.json({ detail: "Informe o e-mail." }, { status: 400 });

  const { status, corpo } = await postarSemToken(
    "/auth/registration/resend-email/",
    { email, client: CLIENTE_DO_CADASTRO },
    { ...cabecalhosDoCliente(pedido.headers), "accept-language": "pt-BR" },
  );
  if (status === 429) {
    return NextResponse.json({ detail: "Muitos pedidos em pouco tempo. Espere um minuto e tente de novo." }, { status });
  }
  if (status >= 500) return NextResponse.json(corpo, { status });
  if (status >= 300) return NextResponse.json({ detail: "Não foi possível reenviar o e-mail." }, { status: 400 });
  return NextResponse.json({ email });
}
