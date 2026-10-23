import type { Metadata } from "next";
import { ModulePage } from "@/components/ModulePage";

export const metadata: Metadata = {
  title: "Recurso de glosa",
  description: "Prepare recursos de glosa com evidência clínica e validação TISS.",
};

export default function RecursoPage() {
  return <ModulePage slug="recurso" />;
}
