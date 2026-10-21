import type { Metadata } from "next";
import { HomeContent } from "@/components/HomeContent";

export const metadata: Metadata = {
  title: "Validação TISS",
  description: "Valide, corrija e revalide lotes TISS antes de enviar à operadora.",
};

export default function Home() {
  return <HomeContent />;
}
