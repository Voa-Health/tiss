"use client";

import { CheckCircleFilled } from "@ant-design/icons";
import { Tag, Tooltip } from "antd";
import type { EstadoDaOrg } from "@/lib/org/tipos";

const FONTE: Record<string, string> = { cnes: "pelo CNES", ans: "pela ANS" };

export function SeloDeVerificacao({ org }: { org: Pick<EstadoDaOrg, "tier" | "identity_source" | "type"> }) {
  if (org.tier === "verified") {
    const fonte = org.identity_source ? FONTE[org.identity_source] : "";
    return <Tag color="success" icon={<CheckCircleFilled />}>{fonte ? `Verificada ${fonte}` : "Verificada"}</Tag>;
  }
  const como = org.type === "pay" ? "Confira o Registro ANS" : "Informe o CNES";
  return (
    <Tooltip title={`${como} em Configurações TISS para verificar.`}>
      <Tag>Não verificada</Tag>
    </Tooltip>
  );
}
