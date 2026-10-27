import { NextResponse, type NextRequest } from "next/server";
import { caminhoDaConversa, chatDaOrg, COOKIE_DA_CONVERSA, idValido, perfilDoChat, VALIDADE_DA_CONVERSA_S } from "@/lib/chat/conversa";
import { lerHistorico } from "@/lib/chat/historico";
import { chamarBackend } from "@/lib/org/backend";
import { mesmaOrigem, parDoPedido, urlDoBackend } from "@/lib/org/credencial";
import { cabecalhosDoCliente } from "@/lib/org/ip";
import { respostaDoBackend } from "@/lib/org/resposta";

export const dynamic = "force-dynamic";

type Contexto = { params: Promise<{ orgId: string }> };

function falha(codigo: string, status: number, erro: string) {
  return NextResponse.json({ codigo, erro }, { status });
}

async function abrir(pedido: NextRequest, { params }: Contexto) {
  const { orgId } = await params;
  if (!idValido(orgId)) return { erro: falha("org_invalida", 404, "Organização não encontrada.") };
  if (!urlDoBackend() || !perfilDoChat()) return { erro: falha("configuracao_ausente", 503, "Assistente indisponível neste ambiente.") };
  const par = parDoPedido(pedido);
  if (!par) return { erro: falha("sem_sessao", 401, "Entre novamente para abrir o Assistente.") };
  return { orgId, par };
}

export async function GET(pedido: NextRequest, contexto: Contexto) {
  const aberto = await abrir(pedido, contexto);
  if ("erro" in aberto) return aberto.erro;
  const chatId = pedido.cookies.get(COOKIE_DA_CONVERSA)?.value ?? "";
  if (!idValido(chatId)) return NextResponse.json({ chat_id: null, falas: [] });

  const resultado = await chamarBackend(aberto.par, chatDaOrg(aberto.orgId, chatId, "messages/"), { method: "GET" }, cabecalhosDoCliente(pedido.headers));
  if (resultado.status === 404) {
    const resposta = respostaDoBackend({ ...resultado, status: 200, corpo: { chat_id: null, falas: [] } });
    resposta.cookies.delete({ name: COOKIE_DA_CONVERSA, path: caminhoDaConversa(aberto.orgId) });
    return resposta;
  }
  const falas = resultado.status === 200 ? lerHistorico(resultado.corpo) : null;
  if (!falas) return respostaDoBackend({ ...resultado, status: resultado.status === 200 ? 502 : resultado.status, corpo: resultado.status === 200 ? { codigo: "historico_indisponivel", erro: "Não foi possível carregar o histórico da conversa." } : resultado.corpo });
  return respostaDoBackend({ ...resultado, corpo: { chat_id: chatId, falas } });
}

export async function POST(pedido: NextRequest, contexto: Contexto) {
  if (!mesmaOrigem(pedido)) return falha("origem_recusada", 403, "Origem recusada.");
  const aberto = await abrir(pedido, contexto);
  if ("erro" in aberto) return aberto.erro;

  const resultado = await chamarBackend(aberto.par, `/api/v2/org/${aberto.orgId}/chat/`, { method: "POST", body: "{}" }, cabecalhosDoCliente(pedido.headers));
  if (resultado.status !== 201) return respostaDoBackend(resultado);
  const id = (resultado.corpo as { id?: unknown } | null)?.id;
  if (typeof id !== "string" || !idValido(id)) {
    return respostaDoBackend({ ...resultado, status: 502, corpo: { codigo: "resposta_invalida", erro: "O servidor devolveu uma conversa inválida." } });
  }
  const resposta = respostaDoBackend({ ...resultado, corpo: { chat_id: id } });
  resposta.cookies.set(COOKIE_DA_CONVERSA, id, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: caminhoDaConversa(aberto.orgId),
    maxAge: VALIDADE_DA_CONVERSA_S,
  });
  return resposta;
}
