import type { Metadata } from "next";
import { KeyDetails } from "@/components/KeyDetails";

export const metadata: Metadata = {
  title: "Chaves de acesso",
  description: "Consulte e guarde sua chave de acesso.",
};

export default function KeysPage() {
  return <KeyDetails />;
}
