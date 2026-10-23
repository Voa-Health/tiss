/** Caminhos de `/api/v1/` que o painel pode chamar, com os métodos de cada um. */
const ROTAS: { padrao: RegExp; metodos: readonly string[] }[] = [
  { padrao: /^tiss\/organizations\/$/, metodos: ["GET", "POST"] },
  { padrao: /^tiss\/org\/$/, metodos: ["GET"] },
  { padrao: /^tiss\/org\/keys\/$/, metodos: ["GET", "POST"] },
  { padrao: /^tiss\/org\/keys\/[\w-]+\/$/, metodos: ["DELETE"] },
  { padrao: /^tiss\/org\/usage\/$/, metodos: ["GET"] },
  { padrao: /^tiss\/org\/billing\/$/, metodos: ["GET"] },
  { padrao: /^tiss\/org\/billing\/setup\/$/, metodos: ["POST"] },
  { padrao: /^tiss\/org\/billing\/invoices\/$/, metodos: ["GET"] },
  { padrao: /^tiss\/org\/settings\/$/, metodos: ["GET", "PATCH"] },
  { padrao: /^tiss\/org\/audit\/$/, metodos: ["GET", "POST"] },
  { padrao: /^tiss\/org\/audit\/[\w-]+\/$/, metodos: ["GET"] },
  { padrao: /^tiss\/org\/audit\/[\w-]+\/(?:approve|reject)\/$/, metodos: ["POST"] },
  { padrao: /^tiss\/org\/accounts\/$/, metodos: ["GET"] },
  { padrao: /^tiss\/org\/rejection-map\/$/, metodos: ["GET", "DELETE"] },
  { padrao: /^tiss\/org\/rejection-map\/(?:enable|disable)\/$/, metodos: ["POST"] },
  { padrao: /^tiss\/org\/rejection-map\/secret\/$/, metodos: ["GET"] },
  { padrao: /^tiss\/org\/rejection-map\/providers\/$/, metodos: ["GET", "PUT"] },
  { padrao: /^tiss\/org\/accounts\/[\w-]+\/$/, metodos: ["GET"] },
  { padrao: /^tiss\/org\/rules\/$/, metodos: ["GET"] },
  { padrao: /^tiss\/org\/rules\/draft\/$/, metodos: ["PUT"] },
  { padrao: /^tiss\/org\/rules\/validate\/$/, metodos: ["POST"] },
  { padrao: /^tiss\/org\/rules\/diff\/$/, metodos: ["GET"] },
  { padrao: /^tiss\/org\/rules\/publish\/$/, metodos: ["POST"] },
  { padrao: /^tiss\/org\/rules\/versions\/$/, metodos: ["GET"] },
  { padrao: /^tiss\/org\/rules\/official-pr\/$/, metodos: ["GET"] },
  { padrao: /^organization\/members\/$/, metodos: ["GET"] },
  { padrao: /^organization\/members\/[\w-]+\/$/, metodos: ["PATCH", "DELETE"] },
  { padrao: /^organization\/invites\/$/, metodos: ["GET", "POST"] },
  { padrao: /^organization\/invites\/[\w-]+\/(?:resend|cancel)\/$/, metodos: ["POST"] },
];

export function rotaPermitida(caminho: string, metodo: string): boolean {
  return ROTAS.some(({ padrao, metodos }) => padrao.test(caminho) && metodos.includes(metodo));
}

export const ROTA_DO_ONBOARDING = "tiss/organizations/";
