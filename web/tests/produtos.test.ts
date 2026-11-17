import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { caminhoDosPrecos, ehPago, produtoDoKind, usoPorProduto, type TabelaDePrecos } from "../lib/org/produtos.ts";

const TABELAS: TabelaDePrecos[] = [
  {
    product: "terminology",
    currency: "BRL",
    items: [
      { kind: "terminology_api_call", label: "Chamada de API", unit: "chamada", unit_amount: "0", monthly_free: 0 },
      { kind: "terminology_free_text", label: "Texto livre", unit: "item", unit_amount: "0.015", monthly_free: 1000 },
    ],
  },
  {
    product: "sncr",
    currency: "BRL",
    items: [{ kind: "sncr_batch_item", label: "Item em lote", unit: "item", unit_amount: "0.005", monthly_free: 0 }],
  },
];

describe("produtos", () => {
  it("monta o caminho do catálogo de preços", () => {
    assert.equal(caminhoDosPrecos("rnds"), "product/rnds/pricing/");
  });

  it("acha o produto pelo catálogo e, sem ele, pelo prefixo do kind", () => {
    assert.equal(produtoDoKind("terminology_free_text", TABELAS), "terminology");
    assert.equal(produtoDoKind("tiss_appeal"), "tiss");
    assert.equal(produtoDoKind("rnds_api_call"), "rnds");
    assert.equal(produtoDoKind("outro_kind"), null);
  });

  it("separa itens pagos dos grátis pelo preço unitário", () => {
    assert.equal(ehPago(TABELAS[0].items[0]), false);
    assert.equal(ehPago(TABELAS[0].items[1]), true);
  });

  it("agrega o uso por produto, na ordem dos produtos", () => {
    const grupos = usoPorProduto(
      [
        { kind: "sncr_batch_item", label: "Item em lote", quantity: 200, estimated_cost_brl: "1.00" },
        { kind: "tiss_appeal", label: "Recurso de glosa", quantity: 2, estimated_cost_brl: "13.80" },
        { kind: "terminology_free_text", label: "Texto livre", quantity: 1500, estimated_cost_brl: 7.5 },
        { kind: "tiss_extractor", label: "Extrator", quantity: 10, estimated_cost_brl: "4.90" },
        { kind: "outro_kind", label: "Outro", quantity: 1, estimated_cost_brl: "9" },
      ],
      TABELAS,
    );
    assert.deepEqual(
      grupos.map((grupo) => [grupo.produto, grupo.quantidade, Number(grupo.custo.toFixed(2)), grupo.kinds.length]),
      [
        ["tiss", 12, 18.7, 2],
        ["terminology", 1500, 7.5, 1],
        ["sncr", 200, 1, 1],
      ],
    );
  });
});
