import type { Metadata } from "next";
import { HomeContent } from "@/components/HomeContent";

export const metadata: Metadata = {
  title: "TISS aberto para operadoras, prestadores, pacientes e SUS",
  description:
    "Validação, autorização e auditoria TISS offline, operadora simulada, módulos com agente e dados abertos da ANS para operadoras, prestadores, pacientes e gestores públicos.",
};

export default function Home() {
  return <HomeContent />;
}
