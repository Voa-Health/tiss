import type { Metadata } from "next";
import { ModulePage } from "@/components/ModulePage";

export const metadata: Metadata = {
  title: "Voa TISS Cloud",
  description: "Acompanhe lotes, demonstrativos, glosas e regras em um só lugar.",
};

export default function CloudPage() {
  return <ModulePage slug="cloud" />;
}
