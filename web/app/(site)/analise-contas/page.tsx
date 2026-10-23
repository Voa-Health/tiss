import type { Metadata } from "next";
import { ModulePage } from "@/components/ModulePage";

export const metadata: Metadata = {
  title: "Análise de contas",
  description: "Pré-analise 100% das contas recebidas: o agente propõe a glosa com regra citada e o auditor decide.",
};

export default function AnaliseContasPage() {
  return <ModulePage slug="analise_contas" />;
}
