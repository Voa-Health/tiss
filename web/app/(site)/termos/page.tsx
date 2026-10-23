import type { Metadata } from "next";
import { TermsContent } from "@/components/TermsContent";

export const metadata: Metadata = {
  title: "Termos",
  description: "Termos de uso do site tiss.",
};

export default function TermsPage() {
  return <TermsContent />;
}
