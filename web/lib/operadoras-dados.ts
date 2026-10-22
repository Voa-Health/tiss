import fs from "node:fs";
import { repositoryPath } from "@/lib/content";
import type { FontePainel, Operadora, Semestre } from "@/lib/operadoras";

type Painel = { fonte: FontePainel; records: Record<string, (string | number | null | string[])[][]> };

let cache: { operadoras: Operadora[]; painel: Painel } | undefined;

function dados() {
  if (!cache) {
    const read = (name: string) =>
      JSON.parse(fs.readFileSync(repositoryPath("src", "voa_tiss", "operadoras", "_data", name), "utf8"));
    const records: Record<string, Operadora> = read("healthplans.json").records;
    cache = { operadoras: Object.values(records), painel: read("indicadores.json") };
  }
  return cache;
}

export function readOperadoras(): Operadora[] {
  return dados().operadoras;
}

export function fontePainel(): FontePainel {
  return dados().painel.fonte;
}

export function readSerie(registro: string): Semestre[] {
  return (dados().painel.records[registro] ?? []).map((linha) => ({
    periodo: linha[0] as string,
    valores: linha.slice(1, -1) as (number | null)[],
    inconsistentes: linha[linha.length - 1] as string[],
  }));
}
