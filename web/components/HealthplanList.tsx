"use client";

import { Input, theme } from "antd";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import Link from "next/link";
import { useState } from "react";
import type { Operadora } from "@/lib/operadoras";

export function HealthplanList({
  operadoras,
}: {
  operadoras: Pick<Operadora, "registro_ans" | "razao_social">[];
}) {
  const { token } = theme.useToken();
  const [busca, setBusca] = useState("");
  const termo = busca.trim().toLocaleLowerCase("pt-BR");
  const visiveis = termo
    ? operadoras.filter(
        ({ registro_ans, razao_social }) =>
          registro_ans.includes(termo) ||
          razao_social.toLocaleLowerCase("pt-BR").includes(termo),
      )
    : [];

  return (
    <Section
      id="operadoras-ativas"
      title="Operadoras ativas na ANS"
      description={`${operadoras.length} operadoras com perfil, indicadores de glosa e rede hospitalar.`}
    >
      <Input.Search
        allowClear
        placeholder="Nome ou registro ANS"
        aria-label="Buscar operadora"
        value={busca}
        onChange={(event) => setBusca(event.target.value)}
        style={{ maxWidth: token.screenXS }}
      />
      {termo && visiveis.length === 0 && (
        <EmptyState
          title="Nenhuma operadora encontrada"
          description="Busque pelo nome ou pelo registro ANS."
        />
      )}
      <ul
        style={{
          columns: "280px",
          columnGap: token.marginXL,
          margin: 0,
          paddingInlineStart: token.paddingMD,
        }}
      >
        {visiveis.map(({ registro_ans, razao_social }) => (
          <li
            key={registro_ans}
            style={{ breakInside: "avoid", marginBottom: token.marginXXS }}
          >
            <Link href={`/operadoras/${registro_ans}`}>
              {registro_ans} · {razao_social}
            </Link>
          </li>
        ))}
      </ul>
    </Section>
  );
}
