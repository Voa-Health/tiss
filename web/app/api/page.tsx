import type { Metadata } from "next";
import { ApiReference } from "@/components/ApiReference";
import { readOpenApi } from "@/lib/content";

export const metadata: Metadata = {
  title: "Referência da API",
  description: "Operações HTTP e endpoint MCP do voa-tiss.",
};

export default function ApiPage() {
  return <ApiReference api={readOpenApi()} />;
}
