"use client";

import { CheckCircleFilled, ExclamationCircleOutlined } from "@ant-design/icons";
import { Tag, Tooltip } from "antd";
import type { EstadoDaOrg } from "@/lib/org/tipos";

const FONTE: Record<string, string> = { cnes: "pelo CNES", ans: "pela ANS" };

export function SeloDeVerificacao({ org }: { org: Pick<EstadoDaOrg, "tier" | "identity_source" | "type"> }) {
  if (org.tier === "verified") {
    const fonte = org.identity_source ? FONTE[org.identity_source] : "";
    return <Tag color="success" icon={<CheckCircleFilled />}>{fonte ? `Verificada ${fonte}` : "Verificada"}</Tag>;
  }
  const como = org.type === "pay"
    ? "Confira o Registro ANS em Configurações TISS."
    : "Confira o CNPJ e escolha a unidade do CNES em Configurações TISS.";
  return (
    <Tooltip title={`Ainda não batemos esta organização com o registro oficial. Tudo funciona igual; ${como}`}>
      <Tag icon={<ExclamationCircleOutlined />}>Não verificada</Tag>
    </Tooltip>
  );
}
