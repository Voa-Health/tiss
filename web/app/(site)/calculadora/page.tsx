import type { Metadata } from "next";
import { Suspense } from "react";
import { Calculator } from "@/components/Calculator";

export const metadata: Metadata = {
  title: "Calculadora de economia",
  description: "Estime o custo mensal de recursos de glosa com o módulo Voa TISS.",
};

export default function CalculatorPage() {
  return (
    <Suspense fallback={null}>
      <Calculator />
    </Suspense>
  );
}
