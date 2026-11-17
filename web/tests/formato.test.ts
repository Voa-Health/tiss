import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { brl, brlUnitario } from "../lib/org/formato.ts";

describe("formato", () => {
  it("mantém frações de centavo no preço unitário", () => {
    assert.equal(brlUnitario("0.005").replace(/\s/g, " "), "R$ 0,005");
    assert.equal(brlUnitario("0.015").replace(/\s/g, " "), "R$ 0,015");
    assert.equal(brlUnitario("6.90").replace(/\s/g, " "), "R$ 6,90");
    assert.equal(brl("13.80").replace(/\s/g, " "), "R$ 13,80");
  });
});
