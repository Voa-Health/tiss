import type { Metadata } from "next";
import { VerificarEmail } from "@/components/org/VerificarEmail";

export const metadata: Metadata = {
  title: "Confirmar e-mail",
  description: "Confirme o e-mail da sua conta Voa para criar a organização no tiss.",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function VerificarPage({ searchParams }: { searchParams: Promise<{ key?: string | string[] }> }) {
  const { key } = await searchParams;
  return <VerificarEmail chave={(Array.isArray(key) ? key[0] : key) ?? ""} />;
}
