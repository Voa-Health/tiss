import fs from "node:fs";
import path from "node:path";
import { repositoryPath } from "@/lib/content";

export type RulePack = {
  operadora: string;
  mantenedor: { tipo: string; registro_ans?: string };
  official: boolean;
  versao_tiss: string;
  regras: { id: string; descricao: string; severity: string; source: { url: string } }[];
  razaoSocial: string;
};

export const SYNTHETIC_HEALTHPLAN_REGISTRO = "000000";

type PackFile = Omit<RulePack, "operadora" | "razaoSocial">;
type HealthplanIndex = { records: Record<string, { razao_social?: string }> };

export function readRulePacks(): RulePack[] {
  const directory = repositoryPath("src", "tiss", "rules");
  if (!fs.existsSync(directory)) return [];
  const healthplans = JSON.parse(
    fs.readFileSync(repositoryPath("src", "tiss", "operadoras", "_data", "healthplans.json"), "utf8"),
  ) as HealthplanIndex;
  return fs
    .readdirSync(directory)
    .filter((file) => file.endsWith(".json") && file !== `${SYNTHETIC_HEALTHPLAN_REGISTRO}.json`)
    .sort()
    .map((file) => {
      const pack = JSON.parse(fs.readFileSync(path.join(directory, file), "utf8")) as PackFile;
      const registro = file.replace(/\.json$/, "");
      return {
        ...pack,
        operadora: registro,
        razaoSocial: healthplans.records[registro]?.razao_social ?? "Operadora não identificada",
      };
    });
}
