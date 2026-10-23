import fs from "node:fs";
import type { Metadata } from "next";
import { Playground } from "@/components/Playground";
import { repositoryPath } from "@/lib/content";

export const metadata: Metadata = {
  title: "Playground",
  description: "Valide um XML TISS ou simule o envio à operadora.",
};

export default function PlaygroundPage() {
  const examples = repositoryPath("src", "tiss", "examples");
  const errorExample = fs.readFileSync(`${examples}/lote-com-erros.xml`, "utf8");
  const validExample = fs.readFileSync(`${examples}/lote-valido.xml`, "utf8");
  return <Playground errorExample={errorExample} validExample={validExample} />;
}
