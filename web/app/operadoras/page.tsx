import type { Metadata } from "next";
import { Flex } from "antd";
import { OperatorList } from "@/components/OperatorList";
import { OperatorsContent } from "@/components/OperatorsContent";
import { OperatorPublishing } from "@/components/OperatorPublishing";
import { readOperadoras } from "@/lib/operadoras-dados";
import { readRulePacks } from "@/lib/rule-packs";

export const metadata: Metadata = {
  title: "Operadoras",
  description: "Operadoras ativas na ANS, indicadores públicos de glosa e pacotes de regras declarativas.",
};

export default function OperatorsPage() {
  const operadoras = readOperadoras().map(({ registro_ans, razao_social }) => ({ registro_ans, razao_social }));
  return (
    <Flex vertical gap={24}>
      <OperatorsContent packs={readRulePacks()} />
      <OperatorPublishing />
      <OperatorList operadoras={operadoras} />
    </Flex>
  );
}
