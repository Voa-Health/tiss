import { NextResponse, type NextRequest } from "next/server";
import { postarSemToken } from "@/lib/org/backend";
import { gravarPar, mesmaOrigem } from "@/lib/org/credencial";

export const dynamic = "force-dynamic";

export async function POST(pedido: NextRequest) {
  if (!mesmaOrigem(pedido)) return NextResponse.json({ detail: "Origem recusada." }, { status: 403 });
  const dados = (await pedido.json().catch(() => null)) as { email?: unknown; senha?: unknown } | null;
  const email = typeof dados?.email === "string" ? dados.email.trim().toLowerCase() : "";
  const senha = typeof dados?.senha === "string" ? dados.senha : "";
  if (!email || !senha) return NextResponse.json({ detail: "Informe e-mail e senha." }, { status: 400 });

  const { status, corpo } = await postarSemToken("/auth/login/", { email, password: senha });
  if (status >= 500) return NextResponse.json(corpo, { status });
  const { access, refresh } = (corpo ?? {}) as { access?: unknown; refresh?: unknown };
  if (status !== 200 || typeof access !== "string" || typeof refresh !== "string") {
    return NextResponse.json({ detail: "E-mail ou senha inválidos." }, { status: 401 });
  }
  const resposta = NextResponse.json({ ok: true });
  gravarPar(resposta, { access, refresh });
  return resposta;
}
