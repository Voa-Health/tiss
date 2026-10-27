import { NextResponse, type NextRequest } from "next/server";
import { cabecalhoDoCursor, chatDaOrg, idValido } from "@/lib/chat/conversa";
import { chamarBackend } from "@/lib/org/backend";
import { parDoPedido } from "@/lib/org/credencial";
import { cabecalhosDoCliente } from "@/lib/org/ip";
import { respostaDoBackend } from "@/lib/org/resposta";

export const dynamic = "force-dynamic";

type Params = { orgId: string; chatId: string; runId: string };

export async function GET(pedido: NextRequest, { params }: { params: Promise<Params> }) {
  const { orgId, chatId, runId } = await params;
  if (![orgId, chatId, runId].every(idValido)) return NextResponse.json({ detail: "Resposta não encontrada." }, { status: 404 });
  const par = parDoPedido(pedido);
  if (!par) return NextResponse.json({ detail: "Entre novamente para abrir o Assistente." }, { status: 401 });
  const resultado = await chamarBackend(
    par,
    chatDaOrg(orgId, chatId, `runs/${runId}/stream/`),
    { method: "GET", cabecalhos: cabecalhoDoCursor(pedido), signal: pedido.signal },
    cabecalhosDoCliente(pedido.headers),
  );
  return respostaDoBackend(resultado);
}
