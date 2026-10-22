import type { Metadata } from "next";
import { Flex } from "antd";
import { HealthplanList } from "@/components/HealthplanList";
import { HealthplansContent } from "@/components/HealthplansContent";
import { HealthplanPublishing } from "@/components/HealthplanPublishing";
import { readOperadoras } from "@/lib/operadoras-dados";
import { readRulePacks } from "@/lib/rule-packs";

export const metadata: Metadata = {
  title: "Operadoras",
  description: "Operadoras ativas na ANS, indicadores públicos de glosa e pacotes de regras declarativas.",
};

export default function HealthplansPage() {
  const operadoras = readOperadoras().map(({ registro_ans, razao_social }) => ({ registro_ans, razao_social }));
  return (
    <Flex vertical gap={24}>
      <HealthplansContent packs={readRulePacks()} />
      <HealthplanPublishing />
      <HealthplanList operadoras={operadoras} />
    </Flex>
  );
}
