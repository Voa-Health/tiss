export type OrgType = "prov" | "pay" | "bus";
export type Org = {
  nome: string;
  cnpj: string;
  tipo: OrgType;
  registro_ans: string | null;
  cnpj_verificado: boolean;
  termos: { versao: "2026-10"; aceito_por: string; aceito_em: string } | null;
};

export type OrgKey = {
  id: string;
  prefixo: string;
  membro_email: string;
  nivel: "login" | "verified";
  expira_em: number;
  ultimo_uso: number | null;
};

export type UsageDay = {
  dia: string;
  validate: number;
  sandbox: number;
  mcp: number;
};

export type Member = {
  id: string;
  nome: string;
  email: string;
  papel: "admin" | "membro";
};

export type TissSettings = {
  padrao: "4.03.00";
  max_guias_por_lote: number;
  operadoras_em_uso: string[];
};

export type OrgData = {
  org: Org;
  keys: OrgKey[];
  usage: UsageDay[];
  members: Member[];
  tiss: TissSettings;
};

export type OrgDemoState = "normal" | "erro" | "vazio";

const daySeconds = 24 * 60 * 60;
const usageStart = Date.UTC(2026, 8, 22);
const mockNow = Date.parse("2026-10-21T14:00:00-03:00") / 1000;
const unusedKeyIssuedAt = mockNow - 4 * 60 * 60;
const usedKeyLastUse = Date.parse("2026-10-21T10:30:00-03:00") / 1000;

function createUsage(): UsageDay[] {
  return Array.from({ length: 30 }, (_, index) => ({
    dia: new Date(usageStart + index * daySeconds * 1000).toISOString().slice(0, 10),
    validate: (index * 7 + 4) % 19,
    sandbox: (index * 5 + 2) % 11,
    mcp: (index * 3 + 1) % 8,
  }));
}

export const orgMock: OrgData = {
  org: {
    nome: "Operadora Exemplo",
    cnpj: "00000000000191",
    tipo: "pay",
    registro_ans: "000000",
    cnpj_verificado: true,
    termos: {
      versao: "2026-10",
      aceito_por: "Marina Exemplo",
      aceito_em: "2026-10-20T15:00:00.000Z",
    },
  },
  keys: [
    {
      id: "chave-01",
      prefixo: "vt_3fa9",
      membro_email: "marina@exemplo.com.br",
      nivel: "verified",
      expira_em: usedKeyLastUse + daySeconds,
      ultimo_uso: usedKeyLastUse,
    },
    {
      id: "chave-02",
      prefixo: "vt_8c21",
      membro_email: "rafael@exemplo.com.br",
      nivel: "login",
      expira_em: unusedKeyIssuedAt + daySeconds,
      ultimo_uso: null,
    },
  ],
  usage: createUsage(),
  members: [
    { id: "membro-01", nome: "Marina Exemplo", email: "marina@exemplo.com.br", papel: "admin" },
    { id: "membro-02", nome: "Rafael Exemplo", email: "rafael@exemplo.com.br", papel: "membro" },
  ],
  tiss: {
    padrao: "4.03.00",
    max_guias_por_lote: 100,
    operadoras_em_uso: [],
  },
};

export function maskCnpj(cnpj: string): string {
  if (!/^\d{14}$/.test(cnpj)) return cnpj;
  return `${cnpj.slice(0, 2)}.${cnpj.slice(2, 5)}.***/${cnpj.slice(8, 12)}-${cnpj.slice(12)}`;
}

export async function loadOrg(state: OrgDemoState = "normal"): Promise<OrgData> {
  await new Promise((resolve) => setTimeout(resolve, 280));
  if (state === "erro") throw new Error("Não foi possível carregar a organização.");
  if (state === "vazio") {
    return {
      ...orgMock,
      keys: [],
      usage: [],
      members: [orgMock.members[0]],
    };
  }
  return {
    ...orgMock,
    keys: [...orgMock.keys],
    usage: [...orgMock.usage],
    members: [...orgMock.members],
  };
}
