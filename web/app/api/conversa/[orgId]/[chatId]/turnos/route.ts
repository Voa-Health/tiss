import { NextResponse, type NextRequest } from "next/server";
import { chatDaOrg, idValido, perfilDoChat } from "@/lib/chat/conversa";
import { chamarBackend } from "@/lib/org/backend";
import { mesmaOrigem, parDoPedido } from "@/lib/org/credencial";
import { cabecalhosDoCliente } from "@/lib/org/ip";
import { respostaDoBackend } from "@/lib/org/resposta";

export const dynamic = "force-dynamic";

const TIPOS = new Set(["send", "hitl-resolve"]);

export async function POST(pedido: NextRequest, { params }: { params: Promise<{ orgId: string; chatId: string }> }) {
  if (!mesmaOrigem(pedido)) return NextResponse.json({ detail: "Origem recusada." }, { status: 403 });
  const { orgId, chatId } = await params;
  if (!idValido(orgId) || !idValido(chatId)) return NextResponse.json({ detail: "Conversa não encontrada." }, { status: 404 });
  const perfil = perfilDoChat();
  if (!perfil) return NextResponse.json({ detail: "Assistente indisponível neste ambiente." }, { status: 503 });
  const par = parDoPedido(pedido);
  if (!par) return NextResponse.json({ detail: "Entre novamente para abrir o Assistente." }, { status: 401 });

  const turno = (await pedido.json().catch(() => null)) as Record<string, unknown> | null;
  if (!turno || typeof turno.kind !== "string" || !TIPOS.has(turno.kind)) {
    return NextResponse.json({ detail: "Turno inválido." }, { status: 400 });
  }
  const corpo = turno.kind === "send" ? { ...turno, profile: perfil } : turno;
  const resultado = await chamarBackend(
    par,
    chatDaOrg(orgId, chatId, "turns/"),
    { method: "POST", body: JSON.stringify(corpo), signal: pedido.signal },
    cabecalhosDoCliente(pedido.headers),
  );
  return respostaDoBackend(resultado);
}
