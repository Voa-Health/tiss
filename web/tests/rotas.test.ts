import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { rotaPermitida } from "../lib/org/rotas.ts";

describe("rotaPermitida", () => {
  it("aceita caminhos da v2 com a org na URL", () => {
    assert.equal(rotaPermitida("me/tiss/organization/", "GET"), true);
    assert.equal(rotaPermitida("me/tiss/organization/", "POST"), true);
    assert.equal(rotaPermitida("org/org-1/tiss/", "GET"), true);
    assert.equal(rotaPermitida("org/org-1/product-key/", "GET"), true);
    assert.equal(rotaPermitida("org/org-1/product-key/", "POST"), true);
    assert.equal(rotaPermitida("org/org-1/product-key/chave-1/", "DELETE"), true);
    assert.equal(rotaPermitida("org/org-1/invites/convite-1/resend/", "POST"), true);
  });

  it("aceita o catálogo de preços dos quatro produtos só para leitura", () => {
    for (const produto of ["tiss", "terminology", "rnds", "sncr"]) {
      assert.equal(rotaPermitida(`product/${produto}/pricing/`, "GET"), true);
      assert.equal(rotaPermitida(`product/${produto}/pricing/`, "POST"), false);
    }
    assert.equal(rotaPermitida("product/outro/pricing/", "GET"), false);
    assert.equal(rotaPermitida("product/tiss/", "GET"), false);
  });

  it("recusa os nomes retirados e a busca que o backend não serve", () => {
    assert.equal(rotaPermitida("me/tiss/organizations/", "GET"), false);
    assert.equal(rotaPermitida("me/tiss/organization/lookup/", "GET"), false);
    assert.equal(rotaPermitida("org/org-1/product-keys/", "GET"), false);
  });

  it("recusa método fora da lista e caminho sem org", () => {
    assert.equal(rotaPermitida("org/org-1/tiss/", "DELETE"), false);
    assert.equal(rotaPermitida("tiss/settings/", "GET"), false);
    assert.equal(rotaPermitida("org/org-1/chat/", "POST"), false);
  });
});
