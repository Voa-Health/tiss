import { NextResponse, type NextRequest } from "next/server";
import { chamarBackend, trocarOrganizacao } from "@/lib/org/backend";
import { apagarPar, gravarPar, mesmaOrigem, parDoPedido, type ParDeTokens } from "@/lib/org/credencial";
import { ROTA_DO_ONBOARDING, rotaPermitida } from "@/lib/org/rotas";

export const dynamic = "force-dynamic";

type Contexto = { params: Promise<{ caminho: string[] }> };

function orgCriada(corpo: unknown): string | null {
  if (typeof corpo !== "object" || corpo === null || !("id" in corpo)) return null;
  return typeof corpo.id === "string" && corpo.id ? corpo.id : null;
}

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
  const destino = `/api/v1/${caminho}${pedido.nextUrl.search}`;
  const resultado = await chamarBackend(par, destino, { method: metodo, body: corpo || undefined });
  let parFinal: ParDeTokens | null | undefined = resultado.par;

  const id = caminho === ROTA_DO_ONBOARDING && metodo === "POST" && resultado.status < 300
    ? orgCriada(resultado.corpo)
    : null;
  if (id) {
    const troca = await trocarOrganizacao(parFinal ?? par, id);
    if (troca.par) parFinal = troca.par;
  }

  const resposta = resultado.status === 204
    ? new NextResponse(null, { status: 204 })
    : NextResponse.json(resultado.corpo, { status: resultado.status });
  if (parFinal === null) apagarPar(resposta);
  else if (parFinal) gravarPar(resposta, parFinal);
  return resposta;
}

export { repassar as GET, repassar as POST, repassar as PUT, repassar as PATCH, repassar as DELETE };
