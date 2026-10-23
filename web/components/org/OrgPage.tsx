import type { Metadata } from "next";
import { cookies } from "next/headers";
import { OrgApp } from "@/components/org/OrgApp";
import { COOKIE_DA_ORG, lerPar, urlDoBackend } from "@/lib/org/credencial";
import { readRulePacks } from "@/lib/rule-packs";

export const metadata: Metadata = {
  title: "Organização",
  description: "Chaves, uso, membros e configurações da organização.",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

type SearchParams = { secao?: string | string[]; painel?: string | string[]; nova?: string | string[] };

const primeiro = (valor?: string | string[]) => (Array.isArray(valor) ? valor[0] : valor);

export default async function OrgPage({ searchParams, secao }: { searchParams: Promise<SearchParams>; secao?: string }) {
  const params = await searchParams;
  const conectado = lerPar((await cookies()).get(COOKIE_DA_ORG)?.value) !== null;
  const pacotes = readRulePacks().map((pack) => ({
    registro: pack.mantenedor.registro_ans ?? pack.operadora,
    razaoSocial: pack.razaoSocial,
    regras: pack.regras.length,
  }));

  return (
    <OrgApp
      configurado={urlDoBackend() !== null}
      conectado={conectado}
      secao={secao ?? primeiro(params.secao)}
      painel={primeiro(params.painel) === "assistente"}
      nova={primeiro(params.nova) === "1"}
      pacotes={pacotes}
    />
  );
}
