"""Testes da API, do servidor MCP e da operadora simulada."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import socket
import urllib.request
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

import voa_tiss
from voa_tiss import examples, operadoras
from voa_tiss.codes import CODES
from voa_tiss.sandbox import SandboxError, demonstrativo, enviar_lote
from voa_tiss.server import _auth
from voa_tiss.server._auth import CLIENT_DOCUMENT, BackendError
from voa_tiss.server._http import create_app
from voa_tiss.server._keys import ANONYMOUS_LIMIT, LIMITS, issue_key, read_key, sign
from voa_tiss.server._ops import OPS, token_estimate
from voa_tiss.server._quota import set_counter
from voa_tiss.server._telemetry import set_sink
from voa_tiss.tuss import lookup, search

ROOT = Path(__file__).resolve().parents[1]
HTTP_OK = 200
HTTP_ACCEPTED = 202
HTTP_FOUND = 302
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY = 429
HTTP_UNPROCESSABLE = 422
HTTP_UNAVAILABLE = 503
TUSS_PAGE_SIZE = 200
PROTOCOL_NUMBER_LENGTH = 12


@pytest.fixture(autouse=True)
def server_state(monkeypatch):
    """Isola telemetria, segredo e contador diário entre os testes."""
    monkeypatch.setenv("VOA_TISS_KEY_SECRET", "test-secret")
    monkeypatch.setenv("VOA_AUTH_ISSUER", "https://auth.example")
    used: dict[str, int] = {}
    set_sink(None)
    set_counter(lambda key, ttl: used.update({key: used.get(key, 0) + 1}) or used[key])
    yield
    set_sink(None)
    set_counter(None)


def _bearer(tier: str = "verified") -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_key('org-1', tier)[0]}"}


def _cases() -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    lote = examples.load("lote-valido").decode()
    demonstrativo_oficial = (ROOT / "tests/fixtures/demonstrativo-oficial.xml").read_bytes()
    parsed = voa_tiss.parse_demonstrativo(demonstrativo_oficial)
    reconciliation = voa_tiss.plan_reconciliation([], [])
    sandbox_result = enviar_lote(lote)
    return [
        ("validate", {"xml": lote}, voa_tiss.validate(lote).to_dict()),
        (
            "parse_demonstrativo",
            {"xml": demonstrativo_oficial.decode()},
            {"decisoes": [decision.to_dict() for decision in parsed]},
        ),
        (
            "plan_reconciliation",
            {"decisoes": [], "guias": []},
            {
                "propostas": [],
                "sem_par": [decision.to_dict() for decision in reconciliation.sem_par],
                "ambiguas": [decision.to_dict() for decision in reconciliation.ambiguas],
            },
        ),
        (
            "tuss_lookup",
            {"code": "10101012", "tabela": "22"},
            {"resultados": lookup("10101012", tabela="22", include_expired=True)},
        ),
        (
            "tuss_search",
            {"text": "ressonância magnética", "tabela": "22", "limite": 5},
            {"resultados": search("ressonância magnética", tabela="22", include_expired=False)[:5]},
        ),
        (
            "sadt_missing",
            {"values": {}},
            {"faltando": voa_tiss.sadt_missing({})},
        ),
        ("sadt_catalog", {}, voa_tiss.sadt_catalog()),
        ("operadora_perfil", {"registro_ans": "005711"}, operadoras.perfil("005711")),
        ("sandbox_enviar_lote", {"xml": lote}, sandbox_result),
        (
            "sandbox_demonstrativo",
            {"protocolo": sandbox_result["protocolo"]},
            {
                "protocolo": sandbox_result["protocolo"],
                "xml": demonstrativo(sandbox_result["protocolo"]).decode(),
            },
        ),
    ]


def _factory(app: Any):
    def create_client(
        headers: dict[str, str] | None = None,
        timeout: httpx.Timeout | None = None,
        auth: httpx.Auth | None = None,
    ) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            headers=headers,
            timeout=timeout,
            auth=auth,
        )

    return create_client


async def _mcp_cases(app: Any, cases: list[tuple[str, dict[str, Any], dict[str, Any]]]):
    async with (
        app.router.lifespan_context(app),
        streamablehttp_client(
            "http://test/mcp", headers=_bearer(), httpx_client_factory=_factory(app)
        ) as (
            read_stream,
            write_stream,
            _,
        ),
        ClientSession(read_stream, write_stream) as session,
    ):
        initialized = await session.initialize()
        assert initialized.serverInfo.name == "voa-tiss"
        tools = await session.list_tools()
        definitions = {tool.name: tool for tool in tools.tools}
        assert set(definitions) == {op.tool_name for op in OPS}
        for name, entrada, expected in cases:
            op = next(operation for operation in OPS if operation.name == name)
            tool = definitions[op.tool_name]
            assert tool.inputSchema == op.input_schema
            assert tool.outputSchema == op.output_schema
            result = await session.call_tool(op.tool_name, entrada)
            assert result.isError is False
            assert result.structuredContent == expected
        code_resource = await session.read_resource("tiss://codigos")
        assert json.loads(code_resource.contents[0].text) == CODES
        sadt_resource = await session.read_resource("tiss://sadt/catalogo")
        assert json.loads(sadt_resource.contents[0].text) == voa_tiss.sadt_catalog()
        tuss_resource = await session.read_resource("tiss://tuss/22/1")
        page = json.loads(tuss_resource.contents[0].text)
        assert page["tabela"] == "22"
        assert page["pagina"] == 1
        assert len(page["resultados"]) <= TUSS_PAGE_SIZE
        templates = await session.list_resource_templates()
        assert [item.uriTemplate for item in templates.resourceTemplates] == [
            "tiss://tuss/{tabela}/{pagina}"
        ]
        readme_resource = await session.read_resource("tiss://docs/readme")
        assert readme_resource.contents[0].text
        api_resource = await session.read_resource("tiss://docs/api")
        assert "sandbox_enviar_lote" in api_resource.contents[0].text


def test_http_mcp_parity_and_token_budgets():
    """Compara respostas HTTP, MCP e os limites de tokens."""
    cases = _cases()
    app = create_app()
    routes = {op.name: op for op in OPS}
    with TestClient(app, headers=_bearer()) as client:
        for name, entrada, expected in cases:
            operation = routes[name]
            assert token_estimate(expected) <= operation.max_tokens
            if operation.method == "GET":
                response = client.get(operation.route.format(**entrada))
            else:
                response = client.post(operation.route, json=entrada)
            assert response.status_code == HTTP_OK
            assert response.json() == expected
        xml = examples.load("lote-valido")
        response = client.post(
            "/v1/validate",
            content=xml,
            headers={"Content-Type": "application/xml"},
        )
        assert response.status_code == HTTP_OK
        assert response.json() == voa_tiss.validate(xml).to_dict()
        assert client.get("/openapi.json").status_code == HTTP_OK
        mcp_headers = {"Accept": "application/json, text/event-stream"}
        initialize = client.post(
            "/mcp",
            headers=mcp_headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        assert initialize.status_code == HTTP_OK
        tools = client.post(
            "/mcp",
            headers={**mcp_headers, "MCP-Protocol-Version": "2025-03-26"},
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        assert tools.status_code == HTTP_OK
        assert len(tools.json()["result"]["tools"]) == 12
        assert client.get("/v1/limits").json() == LIMITS
        assert client.post("/v1/validate", json={"xml": 3}).status_code == HTTP_UNPROCESSABLE
        assert client.get("/v1/operadoras/999999").status_code == HTTP_NOT_FOUND
        assert client.get("/v1/operadoras/abc").status_code == HTTP_UNPROCESSABLE
        transient = client.post(
            "/v1/sandbox/lotes",
            json={"xml": xml.decode(), "cenario": "falha_transitoria"},
        )
        assert transient.status_code == HTTP_UNAVAILABLE
        assert transient.headers["retry-after"] == "1"
        permanent = client.post(
            "/v1/sandbox/lotes",
            json={"xml": xml.decode(), "cenario": "falha_permanente"},
        )
        assert permanent.status_code == HTTP_UNPROCESSABLE
        assert (
            client.get("/v1/limits", headers={"Authorization": "Bearer invalid"}).status_code
            == HTTP_UNAUTHORIZED
        )
        assert (
            client.post("/mcp", headers={"Authorization": "Bearer invalid"}).status_code
            == HTTP_UNAUTHORIZED
        )
    asyncio.run(_mcp_cases(create_app(), cases))


def _fake_backend(calls: list[tuple[str, dict[str, str] | None]]):
    def backend(path: str, *, form: dict[str, str] | None = None, token: str = "") -> Any:
        calls.append((path, form))
        if path == "/oauth/token":
            if form and form.get("refresh_token") == "revogado":
                raise BackendError(400)
            return {"access_token": f"at-{len(calls)}", "refresh_token": f"rt-{len(calls)}"}
        assert token.startswith("at-")
        return {
            "organization": {"id": "org-1", "name": "Clínica Exemplo"},
            "user_id": "user-1",
            "tier": "verified",
            "cnpj": "11222333000181",
            "match": "catalog",
            "terms_version": "1",
        }

    return backend


def test_login_keys_tiers_telemetry_and_privacy(monkeypatch, caplog):
    """Verifica login, chaves, níveis, telemetria e privacidade dos logs."""
    monkeypatch.setenv("POSTHOG_KEY", "test-posthog-key")
    calls: list[tuple[str, dict[str, str] | None]] = []
    original_backend = _auth._backend
    monkeypatch.setattr(_auth, "_backend", _fake_backend(calls))
    events: list[tuple[str, dict[str, Any]]] = []
    set_sink(lambda event, properties: events.append((event, properties)))
    marker = "TISS_PRIVACY_MARKER_74a9b4"
    xml = examples.load("lote-valido").decode()
    xml = xml.replace("</mensagemTISS>", f"<!-- {marker} --></mensagemTISS>")
    app = create_app()
    logging.disable(logging.NOTSET)
    logging.getLogger().setLevel(logging.DEBUG)
    for candidate in logging.Logger.manager.loggerDict.values():
        if isinstance(candidate, logging.Logger):
            candidate.setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)
    with TestClient(app, base_url="https://testserver", follow_redirects=False) as client:
        assert client.get("/oauth/client.json").json() == CLIENT_DOCUMENT
        login = client.get("/v1/auth/login")
        assert login.status_code == HTTP_FOUND
        query = dict(httpx.URL(login.headers["location"]).params)
        assert login.headers["location"].startswith("https://auth.example/oauth/authorize?")
        assert query["resource"] == "https://tiss-api.voa.health"
        assert query["scope"] == "voa:tiss"
        assert query["client_id"] == CLIENT_DOCUMENT["client_id"]
        assert query["code_challenge_method"] == "S256"
        callback = client.get("/v1/auth/callback", params={"code": "c", "state": query["state"]})
        fragment = dict(httpx.QueryParams(httpx.URL(callback.headers["location"]).fragment))
        assert read_key(fragment["chave"]) is not None
        rejected = client.get("/v1/auth/callback", params={"code": "c", "state": "outro"})
        assert rejected.headers["location"].endswith("/chaves#erro=login_invalido")
        assert fragment["nivel"] == "verified"
        token_form = calls[0][1] or {}
        assert token_form["grant_type"] == "authorization_code"
        assert token_form["resource"] == query["resource"]
        assert _auth._challenge(token_form["code_verifier"]) == query["code_challenge"]
        assert events.pop() == (
            "tiss_chave_emitida",
            {"tier": "verified", "$process_person_profile": False, "$geoip_disable": True},
        )
        refreshes = [
            ({"refresh_token": fragment["refresh_token"]}, HTTP_OK),
            ({"refresh_token": "revogado"}, HTTP_UNAUTHORIZED),
            ({}, HTTP_UNPROCESSABLE),
        ]
        for body, status in refreshes:
            refreshed = client.post("/v1/keys/refresh", json=body)
            assert refreshed.status_code == status
        assert read_key(client.post("/v1/keys/refresh", json=refreshes[0][0]).json()["chave"])
        monkeypatch.setattr(_auth, "issuer", lambda: "http://127.0.0.1:9")
        monkeypatch.setattr(_auth, "_backend", original_backend)
        assert client.post("/v1/keys/refresh", json=refreshes[0][0]).status_code == 503

        expired = "vt_" + sign("key", {"o": "org-1", "n": "login", "e": 1})
        sandbox = ("/v1/sandbox/lotes", {"xml": examples.load("lote-valido").decode()})
        validate = ("/v1/validate", {"xml": xml})
        tiers = [
            ({}, sandbox, 9, HTTP_OK),
            ({}, sandbox, 10, HTTP_TOO_MANY),
            ({}, validate, 0, HTTP_UNAUTHORIZED),
            (_bearer("login"), validate, 49, HTTP_OK),
            (_bearer("login"), validate, 50, HTTP_TOO_MANY),
            (_bearer("verified"), validate, 999, HTTP_OK),
            (_bearer("verified"), validate, 1000, HTTP_TOO_MANY),
            ({"Authorization": f"Bearer {expired}"}, sandbox, 0, HTTP_UNAUTHORIZED),
            ({"Authorization": "Bearer invalid"}, sandbox, 0, HTTP_UNAUTHORIZED),
        ]
        for headers, (route, body), used, status in tiers:
            set_counter(lambda key, ttl, used=used: used + 1)
            response = client.post(route, json=body, headers=headers)
            assert response.status_code == status, (headers, route, used)
            assert (status == HTTP_TOO_MANY) == ("retry-after" in response.headers)
        requests: list[Any] = []

        def redis(request: Any, timeout: float) -> io.BytesIO:
            requests.append(request)
            if len(requests) > 1:
                raise OSError
            return io.BytesIO(b'[{"result": 11}, {"result": 1}]')

        set_counter(None)
        monkeypatch.setattr(urllib.request, "urlopen", redis)
        monkeypatch.setenv("KV_REST_API_URL", "https://kv.example")
        monkeypatch.setenv("KV_REST_API_TOKEN", "kv-token")
        for status in (HTTP_TOO_MANY, HTTP_UNAVAILABLE):
            assert client.post(sandbox[0], json=sandbox[1]).status_code == status
        assert requests[0].full_url == "https://kv.example/pipeline"
        assert json.loads(requests[0].data)[0][0] == "INCR"
        monkeypatch.delenv("KV_REST_API_URL")
        assert client.post(sandbox[0], json=sandbox[1]).status_code == HTTP_OK
        assert client.post("/v1/validate", json={"xml": xml}).status_code == HTTP_UNAUTHORIZED
        monkeypatch.delenv("VOA_TISS_KEY_SECRET")
        assert client.post("/v1/validate", json={"xml": xml}).status_code == HTTP_OK
        monkeypatch.setenv("VOA_TISS_KEY_SECRET", "test-secret")
        events.clear()
        set_counter(lambda key, ttl: 1)
        assert (
            client.post("/v1/validate", json={"xml": xml}, headers=_bearer()).status_code == HTTP_OK
        )
        event_name, properties = events.pop()
        assert event_name == "tiss_operacao"
        assert set(properties) == {
            "operacao",
            "codigos",
            "registro_ans",
            "versao_tiss",
            "data",
            "$process_person_profile",
            "$geoip_disable",
        }
        assert marker not in str(properties)
        off = {**_bearer(), "X-Voa-Telemetry": "off"}
        assert client.post("/v1/validate", json={"xml": xml}, headers=off).status_code == HTTP_OK
        assert not events
        monkeypatch.delenv("VOA_TISS_KEY_SECRET")
        assert client.get("/v1/auth/login").status_code == HTTP_UNAVAILABLE
        monkeypatch.setenv("VOA_TISS_KEY_SECRET", "test-secret")
        set_counter(lambda key, ttl: 1)
        events.clear()
        domain, registros = next(iter(operadoras._data()["dominios"].items()))
        base = {
            "modulo": "recurso",
            "email": f" Teste@{domain} ",
            "empresa": " Clínica   Exemplo ",
            "volume_mensal": "ate_500",
        }
        accepted = client.post("/v1/lista-de-espera", json=base)
        assert accepted.status_code == HTTP_ACCEPTED
        assert accepted.json() == {"recebido": True}
        assert events == [
            (
                "tiss_waitlist_join",
                {
                    "module": "recurso",
                    "volume_mensal": "ate_500",
                    "org_match": registros,
                    "distinct_id": f"teste@{domain}",
                    "$set": {"email": f"teste@{domain}", "empresa": "Clínica Exemplo"},
                    "$geoip_disable": True,
                },
            )
        ]
        for email, expected in (
            (f"x@faturamento.{domain}", registros),
            ("teste@gmail.com", []),
        ):
            events.clear()
            assert (
                client.post("/v1/lista-de-espera", json={**base, "email": email}).status_code == 202
            )
            assert events[0][1]["org_match"] == expected
        invalid_waitlist = [
            ({**base, "modulo": "extrator"}, HTTP_UNPROCESSABLE),
            (
                {
                    **base,
                    "modulo": "extrator",
                    "tipos_documento": ["guia_pdf"],
                },
                HTTP_ACCEPTED,
            ),
            ({**base, "modulo": "cloud", "tipos_documento": ["guia_pdf"]}, HTTP_UNPROCESSABLE),
            ({**base, "email": "invalido"}, HTTP_UNPROCESSABLE),
            ({**base, "extra": "valor"}, HTTP_UNPROCESSABLE),
        ]
        for body, status in invalid_waitlist:
            result = client.post("/v1/lista-de-espera", json=body)
            assert result.status_code == status
        assert events[-1][1]["tipos_documento"] == ["guia_pdf"]
        assert client.post("/v1/lista-de-espera", content="{").status_code == HTTP_UNPROCESSABLE
        assert (
            client.post("/v1/lista-de-espera", json=["nao", "objeto"]).status_code
            == HTTP_UNPROCESSABLE
        )
        events.clear()

        def broken_sink(event, properties):
            raise RuntimeError("telemetria indisponível")

        set_sink(broken_sink)
        assert client.post("/v1/lista-de-espera", json=base).status_code == HTTP_UNAVAILABLE
        set_sink(None)
        monkeypatch.delenv("POSTHOG_KEY", raising=False)
        assert client.post("/v1/lista-de-espera", json=base).status_code == HTTP_UNAVAILABLE
        monkeypatch.setenv("POSTHOG_KEY", "test-posthog-key")
        set_sink(lambda event, properties: events.append((event, properties)))
        assert "authorization" not in client.post("/v1/lista-de-espera", json=base).request.headers
        use: dict[str, int] = {}
        set_counter(lambda key, ttl: use.update({key: use.get(key, 0) + 1}) or use[key])
        for _ in range(ANONYMOUS_LIMIT):
            assert client.post("/v1/lista-de-espera", json=base).status_code == 202
        limited = client.post("/v1/lista-de-espera", json=base)
        assert limited.status_code == HTTP_TOO_MANY
        assert limited.headers["retry-after"]
        allowed = {
            "module",
            "volume_mensal",
            "org_match",
            "tipos_documento",
            "distinct_id",
            "$set",
            "$geoip_disable",
        }
        assert all(set(properties) <= allowed for _, properties in events)
    assert fragment["chave"] not in caplog.text
    assert fragment["refresh_token"] not in caplog.text

    events.clear()
    monkeypatch.setenv("VOA_TISS_KEY_SECRET", "test-secret")
    mcp_app = create_app()

    async def run_mcp():
        async with mcp_app.router.lifespan_context(mcp_app):
            for headers in ({"X-Voa-Telemetry": "off", **_bearer()}, _bearer(), {}):
                async with (
                    streamablehttp_client(
                        "http://test/mcp",
                        headers=headers,
                        httpx_client_factory=_factory(mcp_app),
                    ) as (read_stream, write_stream, _),
                    ClientSession(read_stream, write_stream) as session,
                ):
                    await session.initialize()
                    result = await session.call_tool("tiss_validate", {"xml": xml})
                    assert result.isError is not bool(headers)
                if "X-Voa-Telemetry" in headers:
                    assert not events
                elif headers:
                    assert [event for event, _ in events] == ["tiss_operacao"]
                else:
                    assert result.structuredContent["erro"]["codigo"] == "chave_obrigatoria"

    asyncio.run(run_mcp())
    assert [event for event, _ in events] == ["tiss_operacao"]
    assert marker not in caplog.text


@pytest.mark.parametrize(
    ("scenario", "expected", "code"),
    [
        ("aprovado", "pago", ""),
        ("duplicidade", "glosado", "1702"),
        ("carteirinha_vencida", "glosado", "1017"),
        ("sem_autorizacao", "glosado", "1402"),
    ],
)
def test_simulated_statement_round_trip(scenario, expected, code, monkeypatch):
    """Valida demonstrativos simulados de aprovação e glosa."""
    lote = examples.load("lote-valido")
    response = enviar_lote(lote, cenario=scenario)
    assert response["aceito"] is True
    assert len(response["numero_protocolo"]) == PROTOCOL_NUMBER_LENGTH
    assert response["protocolo"] == enviar_lote(lote, cenario=scenario)["protocolo"]

    xml = demonstrativo(response["protocolo"])
    assert voa_tiss.validate(xml).valid
    decisions = voa_tiss.parse_demonstrativo(xml)
    assert len(decisions) == len(response["resumo"]["guias"])
    if scenario == "sem_autorizacao":
        assert decisions[0].decision == expected
        assert code in decisions[0].motivo
        assert all(decision.decision == "pago" for decision in decisions[1:])
    else:
        assert all(decision.decision == expected for decision in decisions)
        if code:
            assert all(code in decision.motivo for decision in decisions)

    if scenario != "aprovado":
        return
    with pytest.raises(SandboxError, match="temporária") as transient:
        enviar_lote(lote, cenario="falha_transitoria")
    assert transient.value.codigo == "sandbox.falha_transitoria"
    assert not transient.value.permanente
    retry = enviar_lote(lote, cenario="falha_transitoria", tentativa=2)
    assert all(
        decision.decision == "pago"
        for decision in voa_tiss.parse_demonstrativo(demonstrativo(retry["protocolo"]))
    )
    with pytest.raises(SandboxError) as permanent:
        enviar_lote(lote, cenario="falha_permanente")
    assert permanent.value.codigo == "sandbox.falha_permanente"
    assert permanent.value.permanente

    invalid = enviar_lote(examples.load("lote-com-erros"))
    assert invalid["aceito"] is False
    assert invalid["protocolo"] is None
    assert invalid["findings"]

    def blocked(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setenv("VOA_TISS_API_KEY", "local-key")
    assert voa_tiss.validate(lote).valid
    assert voa_tiss.parse_demonstrativo(examples.load("demonstrativo"))
    assert lookup("10101012", tabela="22")
    assert enviar_lote(lote)["aceito"]
