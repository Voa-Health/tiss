import { NextResponse, type NextRequest } from "next/server";
import { apagarPar, mesmaOrigem } from "@/lib/org/credencial";

export async function POST(pedido: NextRequest) {
  if (!mesmaOrigem(pedido)) return NextResponse.json({ detail: "Origem recusada." }, { status: 403 });
  const resposta = NextResponse.json({ ok: true });
  apagarPar(resposta);
  return resposta;
}
