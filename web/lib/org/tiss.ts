import type { Pagina } from "@/lib/org/tipos";

export type RegraTiss = {
  id?: string;
  nome?: string;
  descricao?: string;
  source?: unknown;
  [campo: string]: unknown;
};

export type PacoteTiss = {
  id: string;
  status: string;
  version: number;
  content: Record<string, unknown>;
  updated_at: string | null;
  updated_by: string | null;
  published_at: string | null;
  published_by: string | null;
};

export type ValidacaoTiss = {
  valid: boolean;
  errors: string[];
  rules_without_source: string[];
};

export type MudancaTiss = {
  id: string;
  fields: string[];
  before: RegraTiss;
  after: RegraTiss;
};

export type DiffTiss = {
  header: string[];
  added: RegraTiss[];
  removed: RegraTiss[];
  changed: MudancaTiss[];
  unchanged: boolean;
};

export type EstadoDasRegras = {
  draft: PacoteTiss | null;
  published: PacoteTiss | null;
  validation: ValidacaoTiss | null;
  diff: DiffTiss | null;
};

export type VersoesDasRegras = Pagina<PacoteTiss>;

export type PayloadDoLinkOficial = {
  repository: string;
  path: string;
  branch: string;
  title: string;
  body: string;
  official: boolean;
  version: number;
  published_at: string;
  content: string;
};

export type ItemDeAuditoria = {
  id: string;
  kind: string;
  kind_display: string;
  status: string;
  numero_guia: string;
  prestador: string | Record<string, unknown>;
  reason: string;
  items: { codigo_glosa?: string; reason?: string; valor_glosa?: number | string; [campo: string]: unknown }[];
  claim_response_id: string | null;
  opened_at: string | null;
  resolution: Record<string, unknown>;
  resolved_at: string | null;
  account?: ContaTiss | null;
};

export type ContaTiss = {
  id: string;
  claim_id: string | null;
  status: string;
  outcome: string;
  kind: string;
  decision: string;
  review_required: boolean;
  numero_guia: string;
  prestador: Record<string, unknown>;
  patient_id: string | null;
  total: { value?: number | string; currency?: string } | number | string | null;
  disposition: Record<string, unknown> | null;
  adjudication: Record<string, unknown> | null;
  auditoria: { decision?: string; [campo: string]: unknown } | null;
  created: string | null;
  claim_items?: Record<string, unknown>[];
};

export type ListaDeAuditoria = Pagina<ItemDeAuditoria>;
export type ListaDeContas = Pagina<ContaTiss>;
