const ORG = String.raw`org\/[\w-]+\/`;
const ID = String.raw`[\w-]+\/`;

/** Caminhos de `/api/v2/` que o painel pode chamar, com os métodos de cada um. */
const ROTAS = ([
  ["me/tiss/organization/", ["GET", "POST"]],
  [String.raw`product\/(?:tiss|terminology|rnds|sncr)\/pricing\/`, ["GET"]],
  [`${ORG}tiss/`, ["GET"]],
  [`${ORG}tiss/onboard/`, ["POST"]],
  [`${ORG}tiss/settings/`, ["GET", "PATCH"]],
  [`${ORG}tiss/audit/`, ["GET"]],
  [`${ORG}tiss/audit/${ID}`, ["GET"]],
  [`${ORG}tiss/audit/${ID}(?:approve|reject)/`, ["POST"]],
  [`${ORG}tiss/account/`, ["GET"]],
  [`${ORG}tiss/rule/`, ["GET"]],
  [`${ORG}tiss/rule/publish/`, ["POST"]],
  [`${ORG}tiss/rule/version/`, ["GET"]],
  [`${ORG}tiss/rule/official-pr/`, ["GET"]],
  [`${ORG}tiss/rejection-map/`, ["GET", "DELETE"]],
  [`${ORG}tiss/rejection-map/(?:enable|disable)/`, ["POST"]],
  [`${ORG}tiss/rejection-map/secret/`, ["GET"]],
  [`${ORG}tiss/rejection-map/provider/`, ["PUT"]],
  [`${ORG}product-key/`, ["GET", "POST"]],
  [`${ORG}product-key/${ID}`, ["DELETE"]],
  [`${ORG}usage/`, ["GET"]],
  [`${ORG}billing/`, ["GET"]],
  [`${ORG}billing/setup/`, ["POST"]],
  [`${ORG}billing/invoice/`, ["GET"]],
  [`${ORG}member/`, ["GET"]],
  [`${ORG}member/area/`, ["GET"]],
  [`${ORG}member/${ID}`, ["PATCH", "DELETE"]],
  [`${ORG}invite/`, ["GET", "POST"]],
  [`${ORG}invite/${ID}`, ["DELETE"]],
  [`${ORG}invite/${ID}resend/`, ["POST"]],
] satisfies [string, string[]][]).map(([caminho, metodos]) => ({ padrao: new RegExp(`^${caminho}$`), metodos }));

export function rotaPermitida(caminho: string, metodo: string): boolean {
  return ROTAS.some(({ padrao, metodos }) => padrao.test(caminho) && metodos.includes(metodo));
}
