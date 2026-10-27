const ORG = String.raw`org\/[\w-]+\/`;
const ID = String.raw`[\w-]+\/`;

/** Caminhos de `/api/v2/` que o painel pode chamar, com os métodos de cada um. */
const ROTAS = ([
  ["me/tiss/organizations/", ["GET", "POST"]],
  ["me/tiss/organizations/lookup/", ["GET"]],
  [`${ORG}tiss/`, ["GET"]],
  [`${ORG}tiss/onboard/`, ["POST"]],
  [`${ORG}tiss/settings/`, ["GET", "PATCH"]],
  [`${ORG}tiss/audit/`, ["GET"]],
  [`${ORG}tiss/audit/${ID}`, ["GET"]],
  [`${ORG}tiss/audit/${ID}(?:approve|reject)/`, ["POST"]],
  [`${ORG}tiss/accounts/`, ["GET"]],
  [`${ORG}tiss/rules/`, ["GET"]],
  [`${ORG}tiss/rules/publish/`, ["POST"]],
  [`${ORG}tiss/rules/versions/`, ["GET"]],
  [`${ORG}tiss/rules/official-pr/`, ["GET"]],
  [`${ORG}tiss/rejection-map/`, ["GET", "DELETE"]],
  [`${ORG}tiss/rejection-map/(?:enable|disable)/`, ["POST"]],
  [`${ORG}tiss/rejection-map/secret/`, ["GET"]],
  [`${ORG}tiss/rejection-map/providers/`, ["PUT"]],
  [`${ORG}product-keys/`, ["GET", "POST"]],
  [`${ORG}product-keys/${ID}`, ["DELETE"]],
  [`${ORG}usage/`, ["GET"]],
  [`${ORG}billing/`, ["GET"]],
  [`${ORG}billing/setup/`, ["POST"]],
  [`${ORG}billing/invoices/`, ["GET"]],
  [`${ORG}members/`, ["GET"]],
  [`${ORG}members/${ID}`, ["PATCH", "DELETE"]],
  [`${ORG}invites/`, ["GET", "POST"]],
  [`${ORG}invites/${ID}(?:resend|cancel)/`, ["POST"]],
] satisfies [string, string[]][]).map(([caminho, metodos]) => ({ padrao: new RegExp(`^${caminho}$`), metodos }));

export function rotaPermitida(caminho: string, metodo: string): boolean {
  return ROTAS.some(({ padrao, metodos }) => padrao.test(caminho) && metodos.includes(metodo));
}
