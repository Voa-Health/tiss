"use client";

import { Input, theme, Typography } from "antd";
import Link from "next/link";
import { useState } from "react";
import type { Operadora } from "@/lib/operadoras";

export function OperatorList({ operadoras }: { operadoras: Pick<Operadora, "registro_ans" | "razao_social">[] }) {
  const { token } = theme.useToken();
  const [busca, setBusca] = useState("");
  const termo = busca.trim().toLocaleLowerCase("pt-BR");
  const visiveis = termo
    ? operadoras.filter(
        ({ registro_ans, razao_social }) =>
          registro_ans.includes(termo) || razao_social.toLocaleLowerCase("pt-BR").includes(termo),
      )
    : operadoras;

  return (
    <section>
      <Typography.Title level={2}>Operadoras ativas na ANS</Typography.Title>
      <Input.Search
        allowClear
        placeholder="Nome ou registro ANS"
        aria-label="Buscar operadora"
        value={busca}
        onChange={(event) => setBusca(event.target.value)}
        style={{ maxWidth: 420, marginBottom: token.marginLG }}
      />
      <ul style={{ columns: "280px", columnGap: token.marginXL, paddingLeft: token.paddingMD }}>
        {visiveis.map(({ registro_ans, razao_social }) => (
          <li key={registro_ans} style={{ breakInside: "avoid", marginBottom: token.marginXXS }}>
            <Link href={`/operadoras/${registro_ans}`}>
              {registro_ans} · {razao_social}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
