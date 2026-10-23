import { NextResponse, type NextRequest } from "next/server";
import { chamarBackend, postarSemToken } from "@/lib/org/backend";
import { COOKIE_DO_NOME, gravarPar, lerNome, mesmaOrigem } from "@/lib/org/credencial";
import { cabecalhosDoCliente } from "@/lib/org/ip";

export const dynamic = "force-dynamic";

export async function POST(pedido: NextRequest) {
  if (!mesmaOrigem(pedido)) return NextResponse.json({ detail: "Origem recusada." }, { status: 403 });
  const dados = (await pedido.json().catch(() => null)) as { key?: unknown } | null;
  const key = typeof dados?.key === "string" ? dados.key.trim() : "";
  if (!key) return NextResponse.json({ detail: "Link de confirmação incompleto." }, { status: 400 });

  const extras = cabecalhosDoCliente(pedido.headers);
  const { status, corpo } = await postarSemToken("/auth/registration/verify-email/", { key }, extras);
  if (status >= 500) return NextResponse.json(corpo, { status });
  const login = (corpo as { login_data?: { access?: unknown; refresh?: unknown } } | null)?.login_data;
  if (status !== 200 || typeof login?.access !== "string" || typeof login.refresh !== "string") {
    return NextResponse.json(
      { detail: "Este link já foi usado ou venceu. Entre com a sua conta ou peça outro e-mail." },
      { status: 400 },
    );
  }

  let par = { access: login.access, refresh: login.refresh };
  const nome = lerNome(pedido);
  if (nome) {
    const perfil = await chamarBackend(par, "/auth/user/", { method: "PATCH", body: JSON.stringify({ name: nome }) }, extras);
    if (perfil.par) par = perfil.par;
  }
  const resposta = NextResponse.json({ ok: true });
  gravarPar(resposta, par);
  resposta.cookies.delete(COOKIE_DO_NOME);
  return resposta;
}
