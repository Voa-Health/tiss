import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { caminhoDaBusca, chaveDaBusca, lerResposta, nomeSugerido, rotuloDaUnidade, situacaoDaBusca } from "../lib/org/busca.ts";

describe("chaveDaBusca", () => {
  it("busca prestador pelo CNPJ completo", () => {
    assert.deepEqual(chaveDaBusca("prov", "11.222.333/0001-81", undefined), { campo: "cnpj", valor: "11222333000181" });
    assert.equal(chaveDaBusca("prov", "11.222.333", undefined), null);
  });

  it("busca operadora pelo Registro ANS", () => {
    assert.deepEqual(chaveDaBusca("pay", "11.222.333/0001-81", "123456"), { campo: "registro_ans", valor: "123456" });
    assert.equal(chaveDaBusca("pay", "11.222.333/0001-81", "12"), null);
  });

  it("monta o caminho do BFF", () => {
    assert.equal(caminhoDaBusca({ campo: "cnpj", valor: "11222333000181" }), "tiss/organizations/lookup/?cnpj=11222333000181");
  });
});

describe("estados da busca", () => {
  it("resolvida sugere o nome oficial e entra verificada", () => {
    const resposta = lerResposta({ status: "resolvida", nome_oficial: "Clínica Exemplo Ltda" });
    const situacao = situacaoDaBusca(resposta, "cnpj");
    assert.equal(situacao.alerta, "success");
    assert.match(situacao.mensagem, /Clínica Exemplo Ltda.*verificada/);
    assert.equal(nomeSugerido("", resposta), "Clínica Exemplo Ltda");
    assert.equal(nomeSugerido("Nome que digitei", resposta), null);
  });

  it("ambigua lista as unidades para escolher", () => {
    const resposta = lerResposta({
      status: "ambigua",
      nome_oficial: "Rede Exemplo SA",
      unidades: [
        { cnes: "1234567", nome: "Unidade Centro", municipio: "Curitiba" },
        { cnes: "7654321", nome: "", municipio: "Londrina" },
        { nome: "sem cnes" },
      ],
    });
    assert.equal(resposta.unidades.length, 2);
    assert.match(situacaoDaBusca(resposta, "cnpj").mensagem, /2 unidades.*Escolha a sua/);
    assert.equal(rotuloDaUnidade(resposta.unidades[0]), "Unidade Centro · Curitiba · CNES 1234567");
    assert.equal(rotuloDaUnidade(resposta.unidades[1]), "Unidade sem nome · Londrina · CNES 7654321");
  });

  it("CNPJ fora do CNES segue sem aviso", () => {
    for (const status of ["ausente", "fora-do-registro"]) {
      const situacao = situacaoDaBusca(lerResposta({ status, nome_oficial: "" }), "cnpj");
      assert.equal(situacao.status, status);
      assert.equal(situacao.mensagem, "");
      assert.deepEqual(situacao.unidades, []);
    }
  });

  it("Registro ANS ausente pede para conferir o número", () => {
    const situacao = situacaoDaBusca(lerResposta({ status: "ausente", nome_oficial: "" }), "registro_ans");
    assert.match(situacao.mensagem, /não encontrado na ANS/);
  });

  it("indisponivel e resposta fora do contrato não travam o cadastro", () => {
    for (const corpo of [{ status: "indisponivel", nome_oficial: "" }, { status: "outro" }, null, "x"]) {
      const situacao = situacaoDaBusca(lerResposta(corpo), "registro_ans");
      assert.equal(situacao.status, "indisponivel");
      assert.match(situacao.mensagem, /verificamos depois/);
    }
  });

  it("unidades só valem no estado ambígua", () => {
    const resposta = lerResposta({ status: "resolvida", nome_oficial: "X", unidades: [{ cnes: "1" }] });
    assert.deepEqual(resposta.unidades, []);
  });
});
