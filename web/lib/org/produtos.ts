export const PRODUTOS = ["tiss", "terminology", "rnds", "sncr"] as const;

export type Produto = (typeof PRODUTOS)[number];

export const NOMES_DOS_PRODUTOS: Record<Produto, string> = {
  tiss: "TISS",
  terminology: "Terminologia",
  rnds: "RNDS",
  sncr: "SNCR",
};

export type ItemDePreco = {
  kind: string;
  label: string;
  unit: string;
  unit_amount: string;
  monthly_free: number;
};

export type TabelaDePrecos = {
  product: Produto;
  currency: string;
  items: ItemDePreco[];
};

export type UsoDoKind = {
  kind: string;
  label: string;
  quantity: number;
  estimated_cost_brl: string | number;
};

export type UsoDoProduto = {
  produto: Produto;
  quantidade: number;
  custo: number;
  kinds: UsoDoKind[];
};

export function caminhoDosPrecos(produto: Produto): string {
  return `product/${produto}/pricing/`;
}

export function produtoDoKind(kind: string, tabelas: readonly TabelaDePrecos[] = []): Produto | null {
  const tabela = tabelas.find((item) => item.items.some((preco) => preco.kind === kind));
  if (tabela) return tabela.product;
  return PRODUTOS.find((produto) => kind.startsWith(`${produto}_`)) ?? null;
}

export function ehPago(item: ItemDePreco): boolean {
  return Number(item.unit_amount) > 0;
}

export function usoPorProduto(itens: readonly UsoDoKind[], tabelas: readonly TabelaDePrecos[] = []): UsoDoProduto[] {
  const grupos = new Map<Produto, UsoDoProduto>();
  for (const item of itens) {
    const produto = produtoDoKind(item.kind, tabelas);
    if (!produto) continue;
    const grupo = grupos.get(produto) ?? { produto, quantidade: 0, custo: 0, kinds: [] };
    const custo = Number(item.estimated_cost_brl);
    grupo.quantidade += item.quantity;
    grupo.custo += Number.isFinite(custo) ? custo : 0;
    grupo.kinds.push(item);
    grupos.set(produto, grupo);
  }
  return PRODUTOS.flatMap((produto) => grupos.get(produto) ?? []);
}
