export type AreaDisponivel = { value: string; label: string };

export type Cobranca = {
  enabled?: boolean;
  payment_method_active: boolean;
  payment_method: { brand: string; last4: string; exp_month: number; exp_year: number } | null;
  subscription_status: string | null;
  billing_url: string;
};

export type Fatura = {
  id: string | null;
  number: string | null;
  status: string | null;
  currency: string | null;
  amount_due: number | null;
  amount_paid: number | null;
  total: number | null;
  created: string | null;
  period_start: string | null;
  period_end: string | null;
  hosted_invoice_url: string | null;
  invoice_pdf: string | null;
  member_email: string | null;
};

export type EstadoDaOrg = {
  id: string;
  name: string;
  type: string;
  type_display: string;
  subtype: string;
  subtype_display: string;
  cnpj: string;
  registro_ans: string;
  cnes: string;
  identity_source: "cnes" | "ans" | null;
  insurance_plan_id: string | null;
  tier: "login" | "verified";
  terms: {
    current_version: string;
    url: string;
    accepted: boolean;
    version: string;
    accepted_at: string | null;
    accepted_by: string | null;
  };
  tiss_org: boolean;
  rejection_map?: { eligible: boolean; enabled: boolean };
  is_admin: boolean;
  my_areas: string[];
  available_areas: AreaDisponivel[];
};

export type Subtipo = { code: string; display: string; type: string };

export type CatalogoDeOrgs = {
  organizations: EstadoDaOrg[];
  terms_version: string;
  terms_url: string;
  subtypes: Subtipo[];
};

export type Chave = {
  id: string;
  name: string;
  prefix: string;
  key_tip: string;
  scopes: string[];
  environment: "production" | "sandbox";
  usage_count: number;
  last_used_at: string | null;
  created_at: string;
  created_by: string | null;
};

export type ChaveCriada = Chave & { secret: string };

type UsoPorChave = {
  key_id: string;
  name: string;
  prefix: string;
  revoked: boolean;
  quantity: number;
  by_operation: Record<string, number>;
};

export type Uso = {
  period_start: string;
  period_end: string;
  by_day: { day: string; kind: string; quantity: number }[];
  by_operation: {
    kind: string;
    label: string;
    quantity: number;
    unit_price_brl: string | number;
    free_quantity: number;
    estimated_cost_brl: string | number;
  }[];
  by_key: UsoPorChave[];
  free_calls: {
    total: number;
    by_operation: { operation: string; quantity: number }[];
    by_day: { day: string; operation: string; quantity: number }[];
    by_key: UsoPorChave[];
  };
  estimated_total_brl: string | number;
};

export type Membro = {
  id: string;
  user_id: string | null;
  email: string;
  name: string;
  occupation_label: string;
  areas: string[];
  status: string;
  editable: Record<"occupation" | "clinical_access" | "areas", { editable: boolean; reason: string }>;
  removable: { removable: boolean; reason: string | null };
};

export type Membros = { org_id: string; members: Membro[]; available_areas?: AreaDisponivel[] };

export type Convite = {
  id: string;
  email: string;
  invited_by_name: string;
  created_at: string;
  expires_at: string;
  status: "open" | "expired" | string;
};

export type ConfiguracoesTiss = {
  registro_ans: string;
  cnes: string;
  padrao: string;
  max_guias_por_lote: number | null;
};
