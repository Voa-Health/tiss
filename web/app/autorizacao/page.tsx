import type { Metadata } from "next";
import { ModulePage } from "@/components/ModulePage";

export const metadata: Metadata = {
  title: "Autorização prévia",
  description: "Autorização prévia SP/SADT com agente: aprova por regra e encaminha ao auditor com parecer rascunhado.",
};

export default function AutorizacaoPage() {
  return <ModulePage slug="autorizacao" />;
}
