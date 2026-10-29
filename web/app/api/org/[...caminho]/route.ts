import { NextResponse, type NextRequest } from "next/server";
import { chamarBackend } from "@/lib/org/backend";
import { cabecalhosDoCliente } from "@/lib/org/ip";
import { mesmaOrigem, parDoPedido } from "@/lib/org/credencial";
import { respostaDoBackend } from "@/lib/org/resposta";
import { rotaPermitida } from "@/lib/org/rotas";

export const dynamic = "force-dynamic";

type Contexto = { params: Promise<{ caminho: string[] }> };

async function repassar(pedido: NextRequest, { params }: Contexto) {
  const metodo = pedido.method.toUpperCase();
  if (metodo !== "GET" && !mesmaOrigem(pedido)) {
    return NextResponse.json({ detail: "Origem recusada." }, { status: 403 });
  }
  const caminho = `${(await params).caminho.join("/")}/`;
  if (!rotaPermitida(caminho, metodo)) return NextResponse.json({ detail: "Rota não encontrada." }, { status: 404 });
  const par = parDoPedido(pedido);
  if (!par) return NextResponse.json({ detail: "Entre novamente." }, { status: 401 });

  const corpo = metodo === "GET" || metodo === "DELETE" ? undefined : await pedido.text();
  const resultado = await chamarBackend(
    par,
    `/api/v2/${caminho}${pedido.nextUrl.search}`,
    { method: metodo, body: corpo || undefined },
    cabecalhosDoCliente(pedido.headers),
  );

  return respostaDoBackend(resultado);
}

export { repassar as GET, repassar as POST, repassar as PUT, repassar as PATCH, repassar as DELETE };
