import { PageStack } from "@/components/ui/PageStack";
import type { Metadata } from "next";
import { HealthplanList } from "@/components/HealthplanList";
import { HealthplansContent } from "@/components/HealthplansContent";
import { HealthplanPublishing } from "@/components/HealthplanPublishing";
import { readOperadoras } from "@/lib/operadoras-dados";
import { readRulePacks } from "@/lib/rule-packs";

export const metadata: Metadata = {
  title: "Operadoras",
  description:
    "Checagem na entrada com regras próprias, sandbox, autorização TISS aberta, módulos com agente e dados abertos da ANS sobre operadoras.",
};

export default function HealthplansPage() {
  const operadoras = readOperadoras().map(({ registro_ans, razao_social }) => ({ registro_ans, razao_social }));
  return (
    <PageStack>
      <HealthplansContent packs={readRulePacks()} />
      <HealthplanPublishing />
      <HealthplanList operadoras={operadoras} />
    </PageStack>
  );
}
