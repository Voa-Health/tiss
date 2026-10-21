import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { OperatorProfile } from "@/components/OperatorProfile";
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

export default async function OperatorPage({ params }: Params) {
  const operadora = find((await params).registro);
  if (!operadora) notFound();
  return <OperatorProfile operadora={operadora} serie={readSerie(operadora.registro_ans)} fonte={fontePainel()} />;
}
