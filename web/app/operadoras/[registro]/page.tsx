import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { HealthplanProfile } from "@/components/HealthplanProfile";
import { descricaoOperadora } from "@/lib/operadoras";
import { fontePainel, readOperadoras, readSerie } from "@/lib/operadoras-dados";

type Params = { params: Promise<{ registro: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return readOperadoras().map(({ registro_ans }) => ({ registro: registro_ans }));
}

function find(registro: string) {
  return readOperadoras().find((operadora) => operadora.registro_ans === registro);
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const operadora = find((await params).registro);
  if (!operadora) return {};
  return {
    title: `${operadora.razao_social} · ${operadora.registro_ans}`,
    description: descricaoOperadora(operadora, readSerie(operadora.registro_ans)),
  };
}

export default async function HealthplanPage({ params }: Params) {
  const operadora = find((await params).registro);
  if (!operadora) notFound();
  return <HealthplanProfile operadora={operadora} serie={readSerie(operadora.registro_ans)} fonte={fontePainel()} />;
}
