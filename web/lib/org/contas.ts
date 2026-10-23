export type DadosDoEstadoDaConta = {
  status?: string | null;
  review_required?: boolean;
  auditoria?: { decision?: string | null } | null;
};

export function rotuloDoEstadoDaConta(conta: DadosDoEstadoDaConta): string {
  const decisao = conta.auditoria?.decision;
  if (decisao === "approved") return "Aprovada pela Auditoria";
  if (decisao === "declined") return "Rejeitada pela Auditoria";
  if (conta.status === "draft") return "Aguardando Auditoria";
  if (conta.status === "active" && !conta.review_required) return "Liberada pelo agente";
  if (conta.status === "active") return "Aguardando Auditoria";
  if (conta.status === "cancelled") return "Cancelada";
  return conta.status || "Status indisponível";
}
