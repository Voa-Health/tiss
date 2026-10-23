import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { corpoDoCadastro, falhaDoCadastro, lerCadastro } from "../lib/org/cadastro.ts";

describe("cadastro no /org", () => {
  it("manda o cliente e o canal do voa-tiss", () => {
    const dados = lerCadastro({ email: " Ana@Exemplo.test ", senha: "s3nha-forte", nome: " Ana ", aceite: true });
    assert.ok(dados);
    assert.deepEqual(corpoDoCadastro(dados), {
      email: "ana@exemplo.test",
      password1: "s3nha-forte",
      password2: "s3nha-forte",
      client: "tiss-org",
      channel: "tiss",
    });
  });

  it("exige nome e aceite dos termos", () => {
    assert.equal(lerCadastro({ email: "a@exemplo.test", senha: "x", nome: "", aceite: true }), null);
    assert.equal(lerCadastro({ email: "a@exemplo.test", senha: "x", nome: "Ana", aceite: false }), null);
  });

  it("traduz e-mail já cadastrado e senha fraca", () => {
    const falha = falhaDoCadastro({
      email: ["A user is already registered with this e-mail address."],
      password1: ["This password is too common."],
    });
    assert.match(falha.email ?? "", /Já existe uma conta/);
    assert.match(falha.senha ?? "", /comum demais/);
  });

  it("mantém a mensagem do backend que já vem em português", () => {
    const falha = falhaDoCadastro({ client: ["\"x\" não é um escolha válido."] });
    assert.equal(falha.detail, "Não foi possível criar a conta. Tente de novo.");
    const pendente = falhaDoCadastro({ email: ["Já existe um usuário cadastrado com este endereço de e-mail, mas não foi verificado."] });
    assert.match(pendente.email ?? "", /falta confirmar/);
  });
});
