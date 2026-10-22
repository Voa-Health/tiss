import type { Metadata } from "next";
import { LoginPanel } from "@/components/LoginPanel";

export const metadata: Metadata = {
  title: "Entrar",
  description: "Entre com Voa para obter uma chave de acesso.",
  robots: { index: false, follow: false },
};

export default function LoginPage() {
  return <LoginPanel />;
}
