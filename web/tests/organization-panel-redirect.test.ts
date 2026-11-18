import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { proxy } from "../proxy.ts";

const CONSOLE_URL = "https://console.voa.health";

describe("organization panel redirect", () => {
  for (const path of ["/org", "/org/keys"]) {
    it(`redirects GET ${path} to the Console root`, () => {
      const response = proxy({
        method: "GET",
        nextUrl: new URL(`https://tiss-api.voa.health${path}`),
      });

      assert.ok(response);
      assert.equal(response.status, 308);
      const location = response.headers.get("location");
      assert.ok(location);
      const target = new URL(location);
      assert.equal(target.origin, CONSOLE_URL);
      assert.equal(target.pathname, "/");
      assert.equal(target.search, "");
      assert.equal(target.hash, "");
    });
  }

  it("keeps organization API requests outside the redirect", () => {
    const response = proxy({
      method: "POST",
      nextUrl: new URL("https://tiss-api.voa.health/api/org/entrar"),
    });

    assert.equal(response, undefined);
  });

  it("keeps email verification links outside the redirect", () => {
    const response = proxy({
      method: "GET",
      nextUrl: new URL(
        "/org/verificar?key=synthetic-key",
        "https://tiss-api.voa.health",
      ),
    });

    assert.equal(response, undefined);
  });
});
