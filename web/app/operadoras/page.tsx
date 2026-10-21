import type { Metadata } from "next";
import { OperatorList } from "@/components/OperatorList";
import { OperatorsContent } from "@/components/OperatorsContent";
import { readOperadoras } from "@/lib/operadoras-dados";
import { readRulePacks } from "@/lib/rule-packs";

export const metadata: Metadata = {
  title: "Operadoras",
  description: "Operadoras ativas na ANS, indicadores públicos de glosa e pacotes de regras declarativas.",
};

export default function OperatorsPage() {
  const operadoras = readOperadoras().map(({ registro_ans, razao_social }) => ({ registro_ans, razao_social }));
  return (
    <>
      <OperatorsContent packs={readRulePacks()} />
      <OperatorList operadoras={operadoras} />
    </>
  );
}
