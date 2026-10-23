import { NextResponse, type NextRequest } from "next/server";
import { chamarBackend, renovar } from "@/lib/org/backend";
import {
  apagarPar,
  COOKIE_DA_ORG,
  gravarPar,
  lerPar,
  mesmaOrigem,
  parDoPedido,
  urlDoBackend,
} from "@/lib/org/credencial";
import type { ParDeTokens } from "@/lib/org/credencial";
import { carregarHistorico } from "@/lib/chat/historico";
import type { FalaDoHistorico } from "@/lib/chat/protocolo";

export const dynamic = "force-dynamic";

const COOKIE_DA_CONVERSA = "voa_tiss_conversa";
const VALIDADE_DA_CONVERSA_S = 7 * 24 * 60 * 60;

function configuracao() {
  const backend = urlDoBackend();
  const realtime = process.env.VOA_REALTIME_URL?.trim().replace(/\/+$/, "");
  const profile = process.env.VOA_TISS_CHAT_PROFILE?.trim();
  if (!backend || !realtime || !profile) return null;
  return { backend, realtime, profile };
}

function falha(codigo: string, status: number, erro: string) {
  return NextResponse.json({ codigo, erro }, { status });
}

function persistirPar(resposta: NextResponse, par: ParDeTokens | null) {
  if (par) gravarPar(resposta, par);
  else apagarPar(resposta);
  return resposta;
}

export async function GET(pedido: NextRequest) {
  const config = configuracao();
  if (!config) return falha("configuracao_ausente", 503, "Assistente indisponível neste ambiente.");
  const par = lerPar(pedido.cookies.get(COOKIE_DA_ORG)?.value);
  if (!par) return falha("sem_sessao", 401, "Entre novamente para abrir o Assistente.");
  const renovado = await renovar(par);
  if (!renovado) return persistirPar(falha("sem_sessao", 401, "Entre novamente para abrir o Assistente."), null);

  const chatId = pedido.nextUrl.searchParams.get("chat") || pedido.cookies.get(COOKIE_DA_CONVERSA)?.value || null;
  let falas: FalaDoHistorico[] = [];
  if (pedido.nextUrl.searchParams.get("historico") === "1" && chatId) {
    try {
      falas = await carregarHistorico(config.backend, renovado.access, chatId);
    } catch {
      const resposta = falha("historico_indisponivel", 502, "Não foi possível carregar o histórico da conversa.");
      return persistirPar(resposta, renovado);
    }
  }

  const resposta = NextResponse.json({
    token: renovado.access,
    socket: `${config.realtime}/v1/chat/`,
    chat_id: chatId,
    profile: config.profile,
    falas,
  });
  gravarPar(resposta, renovado);
  return resposta;
}

export async function POST(pedido: NextRequest) {
  if (!mesmaOrigem(pedido)) return falha("origem_recusada", 403, "Origem recusada.");
  const config = configuracao();
  if (!config) return falha("configuracao_ausente", 503, "Assistente indisponível neste ambiente.");
  const par = parDoPedido(pedido);
  if (!par) return falha("sem_sessao", 401, "Entre novamente para abrir o Assistente.");

  const resultado = await chamarBackend(par, "/api/v1/chat/", {
    method: "POST",
    body: JSON.stringify({}),
  });
  if (resultado.status < 200 || resultado.status >= 300) {
    const resposta = NextResponse.json(resultado.corpo, { status: resultado.status });
    if (resultado.par === null) apagarPar(resposta);
    else if (resultado.par) gravarPar(resposta, resultado.par);
    return resposta;
  }
  const dados = resultado.corpo as { id?: unknown } | null;
  if (!dados || typeof dados.id !== "string" || !dados.id) {
    const resposta = falha("resposta_invalida", 502, "O servidor devolveu uma conversa inválida.");
    if (resultado.par) gravarPar(resposta, resultado.par);
    return resposta;
  }

  const resposta = NextResponse.json({ chat_id: dados.id }, { status: 201 });
  if (resultado.par) gravarPar(resposta, resultado.par);
  resposta.cookies.set(COOKIE_DA_CONVERSA, dados.id, {
    httpOnly: false,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: VALIDADE_DA_CONVERSA_S,
  });
  return resposta;
}
