import type { Metadata } from "next";
import { ModulePage } from "@/components/ModulePage";

export const metadata: Metadata = {
  title: "Extrator de documentos TISS",
  description: "Extraia dados de guias e demonstrativos para JSON TISS validado.",
};

export default function ExtratorPage() {
  return <ModulePage slug="extrator" />;
}
