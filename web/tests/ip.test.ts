import assert from "node:assert/strict";
import { afterEach, beforeEach, describe, it } from "node:test";
import { chamarBackend, postarSemToken, trocarOrganizacao } from "../lib/org/backend.ts";
import { cabecalhosDoCliente, ipDoCliente } from "../lib/org/ip.ts";

type Chamada = { url: string; headers: Record<string, string> };

const fetchOriginal = globalThis.fetch;
let chamadas: Chamada[] = [];
let respostas: Response[] = [];

beforeEach(() => {
  process.env.VOA_BACKEND_URL = "https://backend.exemplo.test";
  process.env.TISS_SERVICE_SECRET = "segredo-sintetico";
  chamadas = [];
  respostas = [];
  globalThis.fetch = (async (url: string | URL, init?: RequestInit) => {
    chamadas.push({ url: String(url), headers: Object.fromEntries(new Headers(init?.headers).entries()) });
    return respostas.shift() ?? Response.json({ ok: true });
  }) as typeof fetch;
});

afterEach(() => {
  globalThis.fetch = fetchOriginal;
  delete process.env.TISS_SERVICE_SECRET;
});

describe("ipDoCliente", () => {
  it("usa o primeiro item do x-forwarded-for", () => {
    assert.equal(ipDoCliente(new Headers({ "x-forwarded-for": "203.0.113.7, 10.0.0.1" })), "203.0.113.7");
  });

  it("cai para o x-real-ip", () => {
    assert.equal(ipDoCliente(new Headers({ "x-real-ip": "2001:db8::1" })), "2001:db8::1");
  });

  it("ignora valor que não é IP", () => {
    assert.equal(ipDoCliente(new Headers({ "x-forwarded-for": "localhost.exemplo.test" })), null);
    assert.equal(ipDoCliente(new Headers({ "x-forwarded-for": "999.1.1.1" })), null);
    assert.deepEqual(cabecalhosDoCliente(new Headers()), {});
  });
});

describe("cabecalhosDoCliente", () => {
  it("manda o IP com o segredo de serviço, sem x-forwarded-for", () => {
    assert.deepEqual(cabecalhosDoCliente(new Headers({ "x-forwarded-for": "203.0.113.7" })), {
      "x-voa-client-ip": "203.0.113.7",
      "x-voa-service-secret": "segredo-sintetico",
    });
  });

  it("sem segredo configurado não manda nada", () => {
    delete process.env.TISS_SERVICE_SECRET;
    assert.deepEqual(cabecalhosDoCliente(new Headers({ "x-forwarded-for": "203.0.113.7" })), {});
  });
});

describe("repasse do IP ao backend", () => {
  const extras = { "x-voa-client-ip": "198.51.100.23", "x-voa-service-secret": "segredo-sintetico" };

  it("cadastro sem token leva o IP do navegador", async () => {
    await postarSemToken("/auth/registration/", { email: "ana@exemplo.test" }, extras);
    assert.equal(chamadas[0].url, "https://backend.exemplo.test/auth/registration/");
    assert.equal(chamadas[0].headers["x-voa-client-ip"], "198.51.100.23");
    assert.equal(chamadas[0].headers["x-voa-service-secret"], "segredo-sintetico");
  });

  it("chamada autenticada e renovação do token levam o mesmo IP", async () => {
    respostas = [
      new Response(null, { status: 401 }),
      Response.json({ access: "novo", refresh: "r2" }),
      Response.json({ status: "ausente", nome_oficial: "" }),
    ];
    const resultado = await chamarBackend({ access: "velho", refresh: "r1" }, "/api/v1/tiss/organizations/lookup/?cnpj=1", { method: "GET" }, extras);
    assert.equal(resultado.status, 200);
    assert.deepEqual(chamadas.map((chamada) => chamada.headers["x-voa-client-ip"]), ["198.51.100.23", "198.51.100.23", "198.51.100.23"]);
    assert.equal(chamadas[2].headers.authorization, "Bearer novo");
  });

  it("troca de organização leva o IP", async () => {
    respostas = [Response.json({ access: "a", refresh: "r" })];
    await trocarOrganizacao({ access: "x", refresh: "y" }, "org-1", extras);
    assert.equal(chamadas[0].headers["x-voa-client-ip"], "198.51.100.23");
  });

  it("o cabeçalho de autenticação não pode ser sobrescrito pelos extras", async () => {
    await chamarBackend({ access: "certo", refresh: "r" }, "/x/", { method: "GET" }, { authorization: "Bearer outro" });
    assert.equal(chamadas[0].headers.authorization, "Bearer certo");
  });
});
