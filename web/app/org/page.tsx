import type { Metadata } from "next";
import { OrgBackoffice } from "@/components/OrgBackoffice";
import { OrgPageHeading } from "@/components/OrgPageHeading";
import { orgMock, type OrgDemoState } from "@/lib/org-mock";
import { readRulePacks } from "@/lib/rule-packs";

export const metadata: Metadata = {
  title: "Organização",
  description: "Visão geral, chaves e uso da organização.",
  robots: { index: false, follow: false },
};

type SearchParams = {
  secao?: string | string[];
  papel?: string | string[];
  estado?: string | string[];
};

export default async function OrgPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const first = (value?: string | string[]) => Array.isArray(value) ? value[0] : value;
  const state = first(params.estado);
  const demoState: OrgDemoState =
    state === "erro" || state === "vazio" ? state : "normal";

  return (
    <>
      <OrgPageHeading name={orgMock.org.nome} />
      <OrgBackoffice
        packs={readRulePacks()}
        section={first(params.secao)}
        role={first(params.papel) === "membro" ? "membro" : "admin"}
        demoState={demoState}
      />
    </>
  );
}
