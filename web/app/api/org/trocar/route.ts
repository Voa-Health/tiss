import { NextResponse, type NextRequest } from "next/server";
import { trocarOrganizacao } from "@/lib/org/backend";
import { apagarPar, gravarPar, mesmaOrigem, parDoPedido } from "@/lib/org/credencial";

export const dynamic = "force-dynamic";

export async function POST(pedido: NextRequest) {
  if (!mesmaOrigem(pedido)) return NextResponse.json({ detail: "Origem recusada." }, { status: 403 });
  const par = parDoPedido(pedido);
  if (!par) return NextResponse.json({ detail: "Entre novamente." }, { status: 401 });
  const dados = (await pedido.json().catch(() => null)) as { organization_id?: unknown } | null;
  const id = typeof dados?.organization_id === "string" ? dados.organization_id : "";
  if (!id) return NextResponse.json({ detail: "Informe a organização." }, { status: 400 });

  const resultado = await trocarOrganizacao(par, id);
  const resposta = NextResponse.json(resultado.corpo, { status: resultado.status });
  if (resultado.par === null) apagarPar(resposta);
  else if (resultado.par) gravarPar(resposta, resultado.par);
  return resposta;
}
