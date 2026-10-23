"""Testes da API, do servidor MCP e da operadora simulada."""

from __future__ import annotations

import asyncio
import datetime as dt
import io
import json
import logging
import re
import socket
import threading
import time
import urllib.request
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

import tiss
from scripts._manutencao_ans import _DOMINIOS_GENERICOS
from tiss import dominio, examples, operadoras, sandbox
from tiss import sandbox as sandbox_module
from tiss._glosa import glosa
from tiss.sandbox import _GLOSAS, SandboxError, demonstrativo, enviar_lote
from tiss.server import _docs, _keys, _ops, _published_rules, _rejection_map, _usage
from tiss.server._context import CallContext
from tiss.server._docs import search_docs
from tiss.server._http import create_app
from tiss.server._keys import ANONYMOUS_LIMIT, LIMITS
from tiss.server._ops import OPS, _docs_corpus, call, token_estimate
from tiss.server._ops_schemas import PAID_KINDS, Op, _object
from tiss.server._prompts import PROMPTS
from tiss.server._quota import set_counter
from tiss.server._telemetry import set_sink
from tiss.tuss import lookup, search

ROOT = Path(__file__).resolve().parents[1]
HTTP_OK = 200
HTTP_ACCEPTED = 202
HTTP_FOUND = 302
HTTP_UNAUTHORIZED = 401
HTTP_PAYMENT_REQUIRED = 402
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY = 429
HTTP_UNPROCESSABLE = 422
HTTP_UNAVAILABLE = 503
PROTOCOL_NUMBER_LENGTH = 12


@pytest.fixture(autouse=True)
def server_state(tiss_service):
    """Isola telemetria, chaves e contador diário entre os testes."""
    used: dict[str, int] = {}
    set_sink(None)
    set_counter(lambda key, ttl: used.update({key: used.get(key, 0) + 1}) or used[key])
    yield
    set_sink(None)
    set_counter(None)


def _bearer(tier: str = "verified") -> dict[str, str]:
    return {"Authorization": f"Bearer sk_tiss_{tier}"}


def _cases() -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    xml = examples.load("lote-valido")
    lote = tiss.parse_lote(xml)
    fix_lote = json.loads(
        (ROOT / "tests/fixtures/lotes/corrigivel-valor-divergente.json").read_text()
    )
    fix_report = tiss.check(fix_lote).to_dict()
    audit_context = {"tabela_operadora": {"procedimentos": []}}
    audit_report = tiss.audit(lote, contexto=audit_context, operadora="000000").to_dict()
    assert audit_report["findings"]
    built = tiss.build_lote(lote)
    demonstrativo_oficial = (ROOT / "tests/fixtures/demonstrativo-oficial.xml").read_bytes()
    parsed = tiss.parse_demonstrativo(demonstrativo_oficial)
    reconciliation = tiss.plan_reconciliation([], [])
    sandbox_result = enviar_lote(xml, registro_ans="000000")
    request = json.loads((ROOT / "tests/fixtures/autorizacao-solicitacao.json").read_text())
    authorization_xml = tiss.build_autorizacao(request)
    authorization_response = sandbox.responder_autorizacao(request)
    return [
        ("validate", {"lote": lote}, tiss.check(lote).to_dict()),
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
            {"faltando": tiss.sadt_missing({})},
        ),
        ("sadt_catalog", {}, tiss.sadt_catalog()),
        ("operadora_perfil", {"registro_ans": "005711"}, operadoras.perfil("005711")),
        (
            "sandbox_enviar_lote",
            {"xml": xml.decode(), "registro_ans": "000000"},
            sandbox_result,
        ),
        (
            "autorizacao_build",
            {"mensagem": request},
            {
                "xml": authorization_xml.decode("ISO-8859-1"),
                "hash": tiss.hash_epilogo(authorization_xml),
            },
        ),
        (
            "autorizacao_parse",
            {"xml": authorization_xml.decode("ISO-8859-1")},
            {"mensagem": tiss.parse_autorizacao(authorization_xml)},
        ),
        (
            "autorizacao_check",
            {"solicitacao": request, "contexto": {"operadora": "000000"}},
            tiss.check_autorizacao(request, contexto={"operadora": "000000"}).to_dict(),
        ),
        (
            "sandbox_autorizacao",
            {"solicitacao": request, "cenario": "aprovado"},
            {"xml": authorization_response.decode("ISO-8859-1")},
        ),
        (
            "sandbox_demonstrativo",
            {"protocolo": sandbox_result["protocolo"]},
            {
                "protocolo": sandbox_result["protocolo"],
                "xml": demonstrativo(sandbox_result["protocolo"]).decode(),
            },
        ),
        (
            "build",
            {"lote": lote},
            {"xml": built.decode("ISO-8859-1"), "hash": tiss.hash_epilogo(built)},
        ),
        (
            "hash",
            {"xml": xml.decode("ISO-8859-1")},
            {"hash": tiss.hash_epilogo(xml)},
        ),
        (
            "audit",
            {"lote": lote, "contexto": audit_context, "operadora": "000000"},
            audit_report,
        ),
        (
            "rejection_map",
            {"lotes": [lote]},
            tiss.rejection_map([lote]),
        ),
        (
            "apply_fixes",
            {"lote": fix_lote, "report": fix_report},
            {"lote": tiss.apply_fixes(fix_lote, fix_report)},
        ),
        ("glosa_explain", {"codigo": "1801"}, glosa("1801")),
        ("dominio", {}, {"tabelas": dominio.tables()}),
        (
            "dominio",
            {"tabela": "38", "codigo": "1801"},
            {"resultados": dominio.lookup("38", "1801", include_expired=True)},
        ),
        (
            "dominio",
            {"texto": "glosa", "tabela": "38", "limite": 5},
            {"resultados": dominio.search("glosa", tabela="38", include_expired=False)[:5]},
        ),
        (
            "operadora_lookup",
            {"texto": "005711"},
            {"resultados": operadoras.search("005711", limit=10)},
        ),
        (
            "buscar_docs",
            {"texto": "MCP"},
            {"resultados": search_docs(_docs_corpus(), "MCP", 3)},
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


def test_http_mcp_parity_and_token_budgets(mcp_cases, monkeypatch):
    """Compara respostas HTTP, MCP e os limites de tokens."""

    def missing_metadata(package: str) -> Any:
        raise PackageNotFoundError(package)

    monkeypatch.setattr(_docs, "metadata", missing_metadata)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.strip()
    assert _docs._load_readme() == readme
    cases = _cases()
    assert {name for name, _, _ in cases} == {
        op.name for op in OPS if op.name not in {"rede", "operadora_rede"}
    }
    app = create_app()
    routes = {op.name: op for op in OPS}
    with TestClient(app, headers=_bearer()) as client:
        for name, entrada, expected in cases:
            operation = routes[name]
            assert token_estimate(expected) <= operation.max_tokens
            if operation.method == "GET":
                path_parameters = re.findall(r"\{([^}]+)\}", operation.route)
                route = operation.route.format(**{name: entrada[name] for name in path_parameters})
                params = {
                    name: value for name, value in entrada.items() if name not in path_parameters
                }
                response = client.get(route, params=params)
            else:
                response = client.post(operation.route, json=entrada)
            assert response.status_code == HTTP_OK, (name, response.json())
            assert response.json() == expected
            if name == "buscar_docs":
                assert all(len(item["trecho"]) <= 1200 for item in expected["resultados"])
        xml = examples.load("lote-valido")
        response = client.post(
            "/v1/validate",
            content=xml,
            headers={"Content-Type": "application/xml"},
        )
        assert response.status_code == HTTP_OK
        assert response.json() == tiss.validate(xml).to_dict()
        openapi_response = client.get("/openapi.json")
        assert openapi_response.status_code == HTTP_OK
        openapi = openapi_response.json()
        assert (
            "application/xml" in openapi["paths"]["/v1/validate"]["post"]["requestBody"]["content"]
        )
        assert (
            "application/xml" not in openapi["paths"]["/v1/build"]["post"]["requestBody"]["content"]
        )
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
        tool_definitions = tools.json()["result"]["tools"]
        assert all(tool["inputSchema"].get("type") == "object" for tool in tool_definitions)
        assert all(
            not any(key in tool["inputSchema"] for key in ("oneOf", "anyOf", "allOf"))
            for tool in tool_definitions
        )
        tool_names = [tool["name"] for tool in tool_definitions]
        assert len(tool_names) == len(OPS)
        assert set(tool_names) == {operation.tool_name for operation in OPS}
        reference_files = [
            ROOT / "AGENTS.md",
            *sorted((ROOT / "skills").rglob("*.md")),
            ROOT / ".claude-plugin" / "plugin.json",
            ROOT / "plugin.json",
        ]
        tool_pattern = re.compile(r"`((?:tiss|tuss|glosa|operadora|buscar)_[a-z_]+)`")
        referenced_names = {
            name
            for path in reference_files
            for name in tool_pattern.findall(path.read_text(encoding="utf-8"))
        }
        assert referenced_names, "Nenhuma referência MCP encontrada."
        invalid_names = referenced_names - set(tool_names) - set(PROMPTS)
        assert not invalid_names, (
            f"Referências MCP sem ferramenta ou prompt: {sorted(invalid_names)}"
        )
        assert not any("lista_de_espera" in name for name in tool_names)
        assert all(operation.route != "/v1/lista-de-espera" for operation in OPS)
        assert client.get("/v1/limits").json() == LIMITS
        assert client.post("/v1/validate", json={"xml": 3}).status_code == HTTP_UNPROCESSABLE
        for entrada in ({}, {"xml": "<mensagem/>", "lote": {}}):
            invalid = client.post("/v1/validate", json=entrada)
            assert invalid.status_code == HTTP_UNPROCESSABLE
            assert invalid.json()["erro"]["mensagem"] == (
                "Informe exatamente um dos campos 'xml' ou 'lote'."
            )
        for parametros in ({}, {"cnpj": "11222333000181", "cnes": "1234567"}):
            invalid = client.get("/v1/rede", params=parametros)
            assert invalid.status_code == HTTP_UNPROCESSABLE
            assert invalid.json()["erro"]["mensagem"] == (
                "Informe exatamente um dos campos 'cnpj' ou 'cnes'."
            )
        assert client.get("/v1/operadoras/999999").status_code == HTTP_NOT_FOUND
        assert client.get("/v1/operadoras/abc").status_code == HTTP_UNPROCESSABLE
        assert client.get("/v1/glosas/9999").status_code == HTTP_NOT_FOUND
        assert client.get("/v1/glosas/abc").status_code == HTTP_UNPROCESSABLE
        assert (
            client.get("/v1/dominio", params={"tabela": "999", "codigo": "1"}).status_code
            == HTTP_UNPROCESSABLE
        )
        assert (
            client.get("/v1/dominio", params={"codigo": "1801"}).status_code == HTTP_UNPROCESSABLE
        )
        assert (
            client.get("/v1/dominio", params={"codigo": "1801", "texto": "glosa"}).status_code
            == HTTP_UNPROCESSABLE
        )
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
    with TestClient(create_app()) as anonymous:
        for name, entrada, _ in cases:
            operation = routes[name]
            if name.startswith("sandbox_"):
                continue
            if operation.method == "GET":
                path_parameters = re.findall(r"\{([^}]+)\}", operation.route)
                route = operation.route.format(**{key: entrada[key] for key in path_parameters})
                params = {
                    key: value for key, value in entrada.items() if key not in path_parameters
                }
                response = anonymous.get(route, params=params)
            else:
                response = anonymous.post(operation.route, json=entrada)
            assert response.status_code == HTTP_UNAUTHORIZED, name
    mcp_app = create_app()
    asyncio.run(mcp_cases(mcp_app, cases, _factory(mcp_app), _bearer()))


def test_keys_usage_tiers_telemetry_and_privacy(monkeypatch, caplog, tiss_service):
    """Verifica chaves, escopos, uso, níveis, telemetria e privacidade dos logs."""
    monkeypatch.setenv("POSTHOG_KEY", "test-posthog-key")
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
        sandbox = ("/v1/sandbox/lotes", {"xml": examples.load("lote-valido").decode()})
        validate = ("/v1/validate", {"xml": xml})
        key = "sk_tiss_verified"
        for _ in range(2):
            response = client.post(validate[0], json=validate[1], headers=_bearer())
            assert response.status_code == HTTP_OK
        assert tiss_service.introspections == [key]
        assert key not in repr(_keys._cache)
        tiss_service.revoke(key)
        assert client.post(validate[0], json=validate[1], headers=_bearer()).status_code == 200
        expired_at = time.monotonic() + _keys.CACHE_SECONDS + 1
        monkeypatch.setattr(_keys, "_now", lambda: expired_at)
        revoked = client.post(validate[0], json=validate[1], headers=_bearer())
        assert revoked.status_code == HTTP_UNAUTHORIZED
        assert revoked.json()["erro"]["codigo"] == "chave_invalida"
        monkeypatch.setattr(_keys, "_now", time.monotonic)
        tiss_service.add_key(key)
        _keys.clear_cache()
        tiss_service.add_key("sk_tiss_sandbox", scopes=["tiss:sandbox"])
        only_sandbox = {"Authorization": "Bearer sk_tiss_sandbox"}
        denied = client.post(validate[0], json=validate[1], headers=only_sandbox)
        assert denied.status_code == HTTP_FORBIDDEN
        assert denied.json()["erro"]["codigo"] == "escopo_ausente"
        assert client.post(sandbox[0], json=sandbox[1], headers=only_sandbox).status_code == 200
        assert client.get("/v1/limits", headers=only_sandbox).status_code == HTTP_OK
        tiss_service.down = True
        unknown = {"Authorization": "Bearer sk_tiss_desconhecida"}
        unavailable = client.post(validate[0], json=validate[1], headers=unknown)
        assert unavailable.status_code == HTTP_UNAVAILABLE
        assert unavailable.headers["retry-after"] == "1"
        tiss_service.down = False
        assert client.post(validate[0], json=validate[1], headers=unknown).status_code == 401

        _usage.wait(5)
        tiss_service.batches.clear()
        tiss_service.usage.clear()
        tiss_service.usage_failures = [HTTP_UNAVAILABLE]
        for _ in range(2):
            response = client.post(validate[0], json=validate[1], headers=_bearer())
            assert response.status_code == HTTP_OK
        _usage.wait(5)
        delivered = [event["source_event_id"] for event in tiss_service.usage]
        assert len(delivered) == len(set(delivered)) == 2
        assert [event["source_event_id"] for event in tiss_service.batches[0]] == delivered[:1]
        first = tiss_service.usage[0]
        assert set(first) == {"source_event_id", "key_id", "kind", "occurred_at", "metadata"}
        assert (first["key_id"], first["kind"]) == ("id-verified", "tiss_api_call")
        assert first["metadata"] == {"operation": "validate"}
        assert dt.datetime.fromisoformat(first["occurred_at"]).tzinfo is not None
        tiss_service.usage_failures = [HTTP_UNAVAILABLE] * 20
        started = time.perf_counter()
        response = client.post(validate[0], json=validate[1], headers=_bearer())
        assert response.status_code == HTTP_OK
        assert time.perf_counter() - started < 2
        _usage.wait(5)
        tiss_service.usage_failures = []

        tiers = [
            ({}, sandbox, 9, HTTP_OK),
            ({}, sandbox, 10, HTTP_TOO_MANY),
            ({}, validate, 0, HTTP_UNAUTHORIZED),
            (_bearer("login"), validate, 49, HTTP_OK),
            (_bearer("login"), validate, 50, HTTP_TOO_MANY),
            (_bearer("verified"), validate, 999, HTTP_OK),
            (_bearer("verified"), validate, 1000, HTTP_TOO_MANY),
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
        delivered_before = len(tiss_service.usage)
        monkeypatch.delenv("TISS_BACKEND_URL")
        for headers in ({}, {"Authorization": "Bearer qualquer"}):
            assert client.post(validate[0], json=validate[1], headers=headers).status_code == 200
        _usage.wait(5)
        assert len(tiss_service.usage) == delivered_before
        monkeypatch.setenv("TISS_BACKEND_URL", "https://backend.example")
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
        marked_lote = tiss.parse_lote(examples.load("lote-valido"))
        marked_lote["guias"][0]["dados_solicitante"]["nome_contratado_solicitante"] = marker
        marked_xml = tiss.build_lote(marked_lote).decode("ISO-8859-1")
        marked_request = json.loads(
            (ROOT / "tests/fixtures/autorizacao-solicitacao.json").read_text()
        )
        marked_request["solicitacao"]["dados_beneficiario"]["numero_carteira"] = "CARD-PRIVACY"
        marked_request["solicitacao"]["dados_solicitante"]["profissional_solicitante"][
            "nome_profissional"
        ] = marker
        marked_auth_xml = tiss.build_autorizacao(marked_request).decode("ISO-8859-1")
        marked_auth_response = sandbox_module.responder_autorizacao(marked_request)
        auth_password = tiss.parse_autorizacao(marked_auth_response)["autorizacao"][
            "dados_autorizacao"
        ]["senha"]
        fix_lote = json.loads(
            (ROOT / "tests/fixtures/lotes/corrigivel-valor-divergente.json").read_text()
        )
        fix_lote["guias"][0]["dados_solicitante"]["nome_contratado_solicitante"] = marker
        fix_report = tiss.check(fix_lote).to_dict()
        cpf = "12345678909"
        secret = "s" * 16
        cpf_lote = tiss.parse_lote(examples.load("lote-valido"))
        cpf_lote["prestador"] = {"cpf": cpf}
        cpf_lote["guias"][0]["dados_solicitante"]["nome_contratado_solicitante"] = marker
        privacy_inputs = [
            ("build", {"lote": marked_lote}),
            ("hash", {"xml": marked_xml}),
            ("audit", {"lote": marked_lote, "operadora": "000000"}),
            (
                "rejection_map",
                {"lotes": [cpf_lote], "segredo_pseudonimo": secret},
            ),
            ("autorizacao_build", {"mensagem": marked_request}),
            ("autorizacao_parse", {"xml": marked_auth_xml}),
            ("autorizacao_parse", {"xml": marked_auth_response.decode("ISO-8859-1")}),
            (
                "autorizacao_check",
                {"solicitacao": marked_request, "contexto": {"operadora": "000000"}},
            ),
            (
                "sandbox_autorizacao",
                {"solicitacao": marked_request, "cenario": "aprovado"},
            ),
            ("apply_fixes", {"lote": fix_lote, "report": fix_report}),
            ("glosa_explain", {"codigo": "1801"}),
            ("dominio", {"texto": marker, "tabela": "38"}),
            ("operadora_lookup", {"texto": marker}),
            ("buscar_docs", {"texto": marker}),
        ]
        expected_keys = {
            "operacao",
            "codigos",
            "registro_ans",
            "versao_tiss",
            "data",
            "$process_person_profile",
            "$geoip_disable",
        }
        for name, entrada in privacy_inputs:
            operation = next(op for op in OPS if op.name == name)
            if operation.method == "GET":
                path_parameters = re.findall(r"\{([^}]+)\}", operation.route)
                route = operation.route.format(**{key: entrada[key] for key in path_parameters})
                params = {
                    key: value for key, value in entrada.items() if key not in path_parameters
                }
                response = client.get(route, params=params, headers=_bearer())
            else:
                response = client.post(operation.route, json=entrada, headers=_bearer())
            assert response.status_code == HTTP_OK, (name, response.json())
            event_name, properties = events.pop()
            assert event_name == "tiss_operacao"
            assert set(properties) == expected_keys
            assert marker not in str(properties)
            assert "CARD-PRIVACY" not in str(properties)
            assert auth_password not in str(properties)
            if "lote" in entrada:
                assert properties["registro_ans"] == entrada["lote"]["operadora"]["registro_ans"]
            if name == "rejection_map":
                assert properties["registro_ans"] == "123456"
                assert cpf not in response.text
                assert cpf not in str(properties)
                assert secret not in str(properties)
                assert "hmac" not in str(properties)
        conflict = client.post(
            "/v1/rejection-map",
            json={"lotes": [marked_lote], "operadora": "123456", "regras": {}},
            headers=_bearer(),
        )
        assert conflict.status_code == HTTP_UNPROCESSABLE
        assert conflict.json()["erro"]["mensagem"] == (
            "Informe no máximo um dos campos 'operadora' ou 'regras'."
        )
        events.clear()
        assert (
            client.post(
                "/v1/build",
                json={"lote": marked_lote},
                headers={**_bearer(), "X-Voa-Telemetry": "off"},
            ).status_code
            == HTTP_OK
        )
        assert not events
        set_counter(lambda key, ttl: 1)
        events.clear()
        dominios = operadoras._data()["dominios"]
        assert not (_DOMINIOS_GENERICOS & dominios.keys())
        for generic_domain in ("gmail.com.br", "hotmail.com.br", "uol.com"):
            assert operadoras.por_email(f"x@{generic_domain}") == []
        domain, registros = next(iter(dominios.items()))
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
        for modulo in ("analise_contas", "autorizacao"):
            events.clear()
            assert (
                client.post("/v1/lista-de-espera", json={**base, "modulo": modulo}).status_code
                == 202
            )
            assert events[0][1]["module"] == modulo
        invalid_waitlist = [
            (
                {**base, "modulo": "autorizacao", "tipos_documento": ["guia_pdf"]},
                HTTP_UNPROCESSABLE,
            ),
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
    assert key not in caplog.text

    events.clear()
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
    assert auth_password not in caplog.text
    _check_published_rules_and_paid_modules(monkeypatch, caplog, tiss_service)
    _check_hosted_maps(monkeypatch, caplog, tiss_service)


def _map_workers():
    for worker in threading.enumerate():
        if worker.name == "tiss-map":
            worker.join(5)
            assert not worker.is_alive()


def _check_hosted_maps(monkeypatch, caplog, service):
    set_counter(None)
    lote = tiss.parse_lote(examples.load("lote-valido"))
    lote["prestador"] = {"cpf": "00000000000"}
    expected = tiss.rejection_map([lote], operadora="000000", segredo_pseudonimo="a" * 64)
    with TestClient(create_app()) as client:
        for name in ("validate", "audit"):
            for enabled in (False, True):
                _rejection_map.clear_cache()
                service.map_requests.clear()
                service.map_enabled = enabled
                response = client.post(
                    f"/v1/{name}", json={"lote": lote, "operadora": "000000"}, headers=_bearer()
                )
                assert response.status_code == 200
                _map_workers()
                assert len(service.map_requests) == int(enabled)
                if enabled:
                    assert service.map_requests[0] == {
                        "key": "sk_tiss_verified",
                        "source": "server",
                        "map": expected,
                    }
            for failure in (403, 503):
                _rejection_map.clear_cache()
                service.map_failure = failure
                response = client.post(
                    f"/v1/{name}", json={"lote": lote, "operadora": "000000"}, headers=_bearer()
                )
                assert response.status_code == 200
                _map_workers()
            service.map_failure = 0

        _rejection_map.clear_cache()
        service.map_enabled = True
        assert _rejection_map.secret("sk_tiss_verified") == "a" * 64
        service.map_failure = 503
        for name in ("validate", "audit"):
            assert (
                client.post(
                    f"/v1/{name}", json={"lote": lote, "operadora": "000000"}, headers=_bearer()
                ).status_code
                == 200
            )
            _map_workers()
        service.map_failure = 0

        service.map_requests.clear()
        xml = examples.load("lote-valido").decode("ISO-8859-1")
        assert (
            client.post(
                "/v1/validate", json={"xml": xml, "operadora": "000000"}, headers=_bearer()
            ).status_code
            == 200
        )
        _map_workers()
        assert service.map_requests[0]["map"] == tiss.rejection_map(
            [xml], operadora="000000", segredo_pseudonimo="a" * 64
        )

        _check_map_routes(client, service, expected)
        _check_map_nonblocking(client, monkeypatch, lote)
    assert "00000000000" not in caplog.text
    assert "a" * 64 not in caplog.text


def _check_map_routes(client, service, value):
    _rejection_map.clear_cache()
    service.map_enabled = True
    response = client.get("/v1/rejection-map/config", headers=_bearer())
    assert response.json() == {"enabled": True, "secret": "a" * 64}
    assert response.headers["cache-control"] == "no-store"
    response = client.post("/v1/rejection-map/submit", json=value, headers=_bearer())
    assert response.json() == {"status": "accepted"}
    assert service.map_requests[-1]["source"] == "cli"
    count = len(service.map_requests)
    for extra in (
        {**value, "guia": {}},
        {**value, "prestadores": [{**value["prestadores"][0], "guia": {}}]},
        {
            **value,
            "linhas": [
                {
                    "prestador": "codigo:SINTETICO",
                    "mes": None,
                    "codigo": "TEST",
                    "glosa": None,
                    "rule_id": None,
                    "guias": 1,
                    "valor_afetado": "0.00",
                    "guia": {},
                }
            ],
        },
        {**value, "linhas": [{"prestador": "cpf:00000000000"}]},
    ):
        response = client.post("/v1/rejection-map/submit", json=extra, headers=_bearer())
        assert response.status_code == 400
    assert len(service.map_requests) == count
    for path in ("config", "submit"):
        method = client.get if path == "config" else client.post
        assert method(f"/v1/rejection-map/{path}").status_code == 401
    service.add_key("sk_tiss_no_rules", scopes=["tiss:validate"])
    assert (
        client.get(
            "/v1/rejection-map/config", headers={"Authorization": "Bearer sk_tiss_no_rules"}
        ).status_code
        == 403
    )
    service.map_failure = 503
    assert client.post("/v1/rejection-map/submit", json=value, headers=_bearer()).status_code == 503
    service.map_failure = 0
    service.map_enabled = False
    assert _rejection_map.secret("sk_tiss_verified") == "a" * 64
    assert _rejection_map.secret("sk_tiss_other") is None
    _rejection_map.clear_cache()
    assert client.get("/v1/rejection-map/config", headers=_bearer()).status_code == 403


def _check_map_nonblocking(client, monkeypatch, lote):
    started, release = threading.Event(), threading.Event()

    def blocked_post(path, body):
        started.set()
        assert release.wait(5)
        raise OSError("synthetic backend failure")

    _rejection_map.clear_cache()
    with monkeypatch.context() as patch:
        patch.setattr(_rejection_map, "post", blocked_post)
        try:
            response = client.post(
                "/v1/validate", json={"lote": lote, "operadora": "000000"}, headers=_bearer()
            )
            assert response.status_code == 200
            assert started.wait(1)
        finally:
            release.set()
            _map_workers()


def _check_published_rules_and_paid_modules(monkeypatch, caplog, tiss_service):
    set_counter(None)
    monkeypatch.setenv("TISS_BACKEND_URL", "https://backend.example")
    _published_rules.clear_cache()
    tiss_service.rules_requests.clear()
    package = json.loads((ROOT / "src/tiss/rules/000000.json").read_text())
    tiss_service.rules["org-1"] = package
    xml = examples.load("lote-valido").decode()
    lote = tiss.parse_lote(xml)
    published = [
        ("/v1/validate", {"lote": lote}, tiss.check(lote, operadora=package).to_dict()),
        ("/v1/validate", {"xml": xml}, tiss.validate(xml, operadora=package).to_dict()),
        ("/v1/audit", {"lote": lote}, tiss.audit(lote, operadora=package).to_dict()),
        ("/v1/rejection-map", {"lotes": [lote]}, tiss.rejection_map([lote], operadora=package)),
        ("/v1/sandbox/lotes", {"xml": xml}, enviar_lote(xml, registro_ans=package)),
    ]
    explicit = [
        ("/v1/validate", {"lote": lote, "operadora": "123456"}, tiss.check(lote).to_dict()),
        (
            "/v1/audit",
            {"lote": lote, "operadora": "123456"},
            tiss.audit(lote, operadora="123456").to_dict(),
        ),
        (
            "/v1/rejection-map",
            {"lotes": [lote], "operadora": "123456"},
            tiss.rejection_map([lote], operadora="123456"),
        ),
        ("/v1/sandbox/lotes", {"xml": xml, "registro_ans": "999999"}, enviar_lote(xml)),
    ]
    plain = tiss.check(lote).to_dict()
    assert published[0][2] != plain
    with TestClient(create_app(), base_url="https://testserver") as client:

        def post(route: str, body: dict[str, Any], headers: Any = None) -> Any:
            response = client.post(
                route, json=body, headers=_bearer() if headers is None else headers
            )
            assert response.status_code == HTTP_OK, response.text
            return response.json()

        for route, body, expected in published:
            assert post(route, body) == expected, route
        assert tiss_service.rules_requests == ["sk_tiss_verified"]
        for route, body, expected in explicit:
            assert post(route, body) == expected, route
        assert post("/v1/sandbox/lotes", {"xml": xml}, {}) == enviar_lote(xml)
        assert len(tiss_service.rules_requests) == 1

        expired = time.monotonic() + _keys.CACHE_SECONDS + 1
        monkeypatch.setattr(_published_rules, "_now", lambda: expired)
        tiss_service.rules_failures = [HTTP_UNAVAILABLE]
        caplog.set_level(logging.WARNING, logger="tiss.server")
        assert post("/v1/validate", {"lote": lote}) == plain
        assert "op=regras status=503" in caplog.text
        assert "sk_tiss_verified" not in caplog.text
        assert post("/v1/validate", {"lote": lote}) == published[0][2]
        assert len(tiss_service.rules_requests) == 3
        del tiss_service.rules["org-1"]
        monkeypatch.setattr(_published_rules, "_now", lambda: expired * 2)
        assert post("/v1/validate", {"lote": lote}) == plain
        assert post("/v1/validate", {"lote": lote}) == plain
        assert len(tiss_service.rules_requests) == 4
        monkeypatch.delenv("TISS_BACKEND_URL")
        _published_rules.clear_cache()
        tiss_service.rules["org-1"] = package
        assert post("/v1/validate", {"lote": lote}) == plain
        assert len(tiss_service.rules_requests) == 4
    monkeypatch.setenv("TISS_BACKEND_URL", "https://backend.example")

    billing = {
        "enforced": True,
        "payment_method_active": False,
        "billing_url": "https://painel.example/org/cobranca",
        "cloud_free_remaining": 0,
    }
    payment_required = {
        "code": "payment_required",
        "detail": "Cadastre uma forma de pagamento para usar este módulo.",
        "billing_url": billing["billing_url"],
    }
    default_url = {**payment_required, "billing_url": _keys.BILLING_URL}
    assert {
        "tiss_cloud_guia",
        "tiss_extractor",
        "tiss_appeal",
        "tiss_accounts_review",
        "tiss_authorization",
    } == PAID_KINDS
    cases = [
        ("tiss_extractor", billing, HTTP_PAYMENT_REQUIRED, payment_required),
        ("tiss_appeal", {**billing, "billing_url": None}, HTTP_PAYMENT_REQUIRED, default_url),
        ("tiss_cloud_guia", billing, HTTP_PAYMENT_REQUIRED, payment_required),
        ("tiss_cloud_guia", {**billing, "cloud_free_remaining": 3}, HTTP_OK, {"ok": True}),
        ("tiss_extractor", {**billing, "payment_method_active": True}, HTTP_OK, {"ok": True}),
        ("tiss_extractor", {**billing, "enforced": False}, HTTP_OK, {"ok": True}),
        ("tiss_extractor", None, HTTP_OK, {"ok": True}),
        ("tiss_api_call", billing, HTTP_OK, {"ok": True}),
    ]
    for index, (kind, case_billing, status, expected) in enumerate(cases):
        key = f"sk_tiss_caso{index}"
        tiss_service.add_key(key, billing=case_billing)
        case_access = _keys.resolve(key)
        op = Op(
            "modulo_sintetico",
            lambda value: {"ok": True},
            _object({}),
            _object({}, additional=True),
            "Módulo sintético.",
            10,
            usage_kind=kind,
        )
        monkeypatch.setitem(_ops._VALIDATORS, op.name, _ops._VALIDATORS["sadt_catalog"])
        assert call(op, {}, CallContext(access=case_access)) == (status, expected), index


@pytest.mark.parametrize(
    ("scenario", "expected", "code", "registry", "rule_id"),
    [
        ("aprovado", "pago", "", None, None),
        ("duplicidade", "glosado", "3209", None, None),
        ("carteirinha_vencida", "glosado", "1017", None, None),
        ("sem_autorizacao", "glosado", "1818", None, None),
        ("aprovado", "glosado", "1818", "000000", "exige-autorizacao-consulta"),
        ("aprovado", "pago", "", "999999", None),
        ("autorizacao.aprovado", "1", "", None, None),
        ("autorizacao.pendente", "5", "", None, None),
        ("autorizacao.negado", "3", "3217", None, None),
    ],
)
def test_simulated_statement_round_trip(scenario, expected, code, registry, rule_id, monkeypatch):
    """Valida demonstrativos simulados de aprovação e glosa."""
    if scenario.startswith("autorizacao."):
        cenario = scenario.split(".", 1)[1]
        request = json.loads((ROOT / "tests/fixtures/autorizacao-solicitacao.json").read_text())
        xml = sandbox.responder_autorizacao(request, cenario=cenario)
        assert tiss.validate(xml).valid
        response = tiss.parse_autorizacao(xml)["autorizacao"]
        assert response["status_solicitacao"] == expected
        assert response["dados_autorizacao"]["numero_guia_operadora"]
        assert xml == sandbox.responder_autorizacao(request, cenario=cenario)
        for procedure in response["servicos_autorizados"]:
            assert procedure["quantidade_autorizada"] == (
                procedure["quantidade_solicitada"] if cenario == "aprovado" else "0"
            )
        if cenario == "negado":
            [denial_code] = response["motivos_negativa"]
            assert denial_code == code
            assert glosa(denial_code) is not None
            assert "sintética" in response["observacao"]
        return

    lote = examples.load("lote-valido")
    arguments = {"registro_ans": registry} if registry else {}
    response = enviar_lote(lote, cenario=scenario, **arguments)
    assert response["aceito"] is True
    assert len(response["numero_protocolo"]) == PROTOCOL_NUMBER_LENGTH
    assert response["protocolo"] == enviar_lote(lote, cenario=scenario, **arguments)["protocolo"]
    assert ("regras" in response) is (registry == "000000")
    if rule_id:
        assert any(item["rule"]["id"] == rule_id for item in response["regras"])

    xml = demonstrativo(response["protocolo"])
    assert tiss.validate(xml).valid
    decisions = tiss.parse_demonstrativo(xml)
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
    assert all(glosa(code)["descricao"] == text for code, text in _GLOSAS.values())
    with pytest.raises(SandboxError, match="temporária") as transient:
        enviar_lote(lote, cenario="falha_transitoria")
    assert transient.value.codigo == "sandbox.falha_transitoria"
    assert not transient.value.permanente
    retry = enviar_lote(lote, cenario="falha_transitoria", tentativa=2)
    assert all(
        decision.decision == "pago"
        for decision in tiss.parse_demonstrativo(demonstrativo(retry["protocolo"]))
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
    monkeypatch.setenv("TISS_API_KEY", "local-key")
    assert tiss.validate(lote).valid
    assert tiss.parse_demonstrativo(examples.load("demonstrativo"))
    assert lookup("10101012", tabela="22")
    assert enviar_lote(lote)["aceito"]
