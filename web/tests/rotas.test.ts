import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { rotaPermitida } from "../lib/org/rotas.ts";

describe("rotaPermitida", () => {
  it("aceita caminhos da v2 com a org na URL", () => {
    assert.equal(rotaPermitida("me/tiss/organizations/", "POST"), true);
    assert.equal(rotaPermitida("org/org-1/tiss/", "GET"), true);
    assert.equal(rotaPermitida("org/org-1/product-keys/chave-1/", "DELETE"), true);
    assert.equal(rotaPermitida("org/org-1/invites/convite-1/resend/", "POST"), true);
  });

  it("recusa método fora da lista e caminho sem org", () => {
    assert.equal(rotaPermitida("org/org-1/tiss/", "DELETE"), false);
    assert.equal(rotaPermitida("tiss/settings/", "GET"), false);
    assert.equal(rotaPermitida("org/org-1/chat/", "POST"), false);
  });
});
