import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { carregarTodosOsResultados } from "../lib/org/paginacao.ts";
import type { Pagina } from "../lib/org/tipos.ts";

type Item = { id: string };

describe("carregarTodosOsResultados", () => {
  it("segue o next absoluto pelo caminho do proxy e acumula results", async () => {
    const paginas: Pagina<Item>[] = [
      {
        count: 2,
        next: "https://backend.invalid/api/v2/org/org-1/product-key/?page=2",
        previous: null,
        current_page: 1,
        next_page: 2,
        previous_page: null,
        num_pages: 2,
        results: [{ id: "key-1" }],
      },
      {
        count: 2,
        next: null,
        previous: "https://backend.invalid/api/v2/org/org-1/product-key/",
        current_page: 2,
        next_page: null,
        previous_page: 1,
        num_pages: 2,
        results: [{ id: "key-2" }],
      },
    ];
    const requisicoes: string[] = [];

    const resultados = await carregarTodosOsResultados<Item>("org/org-1/product-key/", async (caminho) => {
      requisicoes.push(caminho);
      return paginas.shift()!;
    });

    assert.deepEqual(requisicoes, ["org/org-1/product-key/", "org/org-1/product-key/?page=2"]);
    assert.deepEqual(resultados, [{ id: "key-1" }, { id: "key-2" }]);
  });
});
