from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import pytest
from lxml import etree
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.exceptions import McpError

import voa_tiss
from voa_tiss import dominio, examples, operadoras, parse_lote
from voa_tiss._schema import parser
from voa_tiss.codes import CODES
from voa_tiss.server import _published_rules, _usage
from voa_tiss.server._keys import clear_cache
from voa_tiss.server._ops import OPS
from voa_tiss.server._service import ServiceError, set_transport

ROOT = Path(__file__).resolve().parents[1]
NS = "http://www.ans.gov.br/padroes/tiss/schemas"
ANS = {"ans": NS}
TUSS_PAGE_SIZE = 200


TISS_SCOPES = ("validate", "build", "sandbox", "accounts", "authorization", "rules")


@dataclass
class FakeService:
    """Backend sintético de chaves e uso."""

    keys: dict[str, dict[str, Any]] = field(default_factory=dict)
    introspections: list[str] = field(default_factory=list)
    batches: list[list[dict[str, Any]]] = field(default_factory=list)
    usage: list[dict[str, Any]] = field(default_factory=list)
    usage_failures: list[int] = field(default_factory=list)
    rules: dict[str, dict[str, Any]] = field(default_factory=dict)
    rules_requests: list[str] = field(default_factory=list)
    rules_failures: list[int] = field(default_factory=list)
    down: bool = False

    def add_key(
        self, key: str, tier: str = "verified", scopes: Any = None, billing: Any = None
    ) -> None:
        self.keys[key] = {
            "active": True,
            "revoked": False,
            "key_id": "id-" + key.removeprefix("sk_tiss_"),
            "organization": {"id": "org-1", "name": "Clínica Exemplo"},
            "scopes": list(scopes or [f"tiss:{scope}" for scope in TISS_SCOPES]),
            "environment": "production",
            "tier": tier,
            "terms_accepted": True,
        }
        if billing is not None:
            self.keys[key]["billing"] = billing

    def revoke(self, key: str) -> None:
        self.keys[key] = {
            "active": False,
            "revoked": True,
            "key_id": "id-" + key.removeprefix("sk_tiss_"),
        }

    def __call__(self, path: str, body: dict[str, Any]) -> Any:
        if path == "/tiss/service/keys/introspect":
            self.introspections.append(body["key"])
            if self.down:
                raise ServiceError(503)
            return self.keys.get(body["key"], {"active": False})
        if path == "/tiss/service/rules":
            self.rules_requests.append(body["key"])
            if self.rules_failures:
                raise ServiceError(self.rules_failures.pop(0))
            org = self.keys[body["key"]]["organization"]["id"]
            if org not in self.rules:
                raise ServiceError(404)
            return {"organization_id": org, "version": 1, "package": self.rules[org]}
        assert path == "/tiss/service/usage"
        self.batches.append(body["events"])
        if self.usage_failures:
            raise ServiceError(self.usage_failures.pop(0))
        self.usage.extend(body["events"])
        return {"accepted": len(body["events"]), "duplicates": 0}


@pytest.fixture
def tiss_service(monkeypatch):
    """Liga o servidor a um backend sintético de chaves e uso."""
    monkeypatch.setenv("VOA_TISS_BACKEND_URL", "https://backend.example")
    monkeypatch.setenv("VOA_TISS_SERVICE_SECRET", "s" * 16)
    monkeypatch.setattr(_usage, "RETRY_SECONDS", 0.0)
    service = FakeService()
    for tier in ("login", "verified"):
        service.add_key(f"sk_tiss_{tier}", tier)
    clear_cache()
    _published_rules.clear_cache()
    set_transport(service)
    yield service
    _usage.wait(5)
    set_transport(None)
    clear_cache()
    _published_rules.clear_cache()


@pytest.fixture
def valid_lote():
    return parse_lote(examples.load("lote-valido"))


@pytest.fixture
def mcp_cases():
    async def run(
        app: Any,
        cases: list[tuple[str, dict[str, Any], dict[str, Any]]],
        client_factory: Callable[..., httpx.AsyncClient],
        headers: dict[str, str],
    ) -> None:
        async with (
            app.router.lifespan_context(app),
            streamablehttp_client(
                "http://test/mcp", headers=headers, httpx_client_factory=client_factory
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
            domain_resource = await session.read_resource("tiss://dominio/tabelas")
            assert json.loads(domain_resource.contents[0].text) == {
                "tabelas": dominio.tables(),
                "fonte": dominio.info(),
            }
            healthplan_resource = await session.read_resource("tiss://operadoras")
            assert json.loads(healthplan_resource.contents[0].text) == operadoras.info()
            rules_resource = await session.read_resource("tiss://regras/schema")
            assert json.loads(rules_resource.contents[0].text) == voa_tiss.json_schema("rules")
            lote_schema_resource = await session.read_resource("tiss://schemas/lote")
            assert json.loads(lote_schema_resource.contents[0].text) == voa_tiss.json_schema("lote")
            tuss_resource = await session.read_resource("tiss://tuss/22/1")
            page = json.loads(tuss_resource.contents[0].text)
            assert page["tabela"] == "22"
            assert page["pagina"] == 1
            assert len(page["resultados"]) <= TUSS_PAGE_SIZE
            domain_table = await session.read_resource("tiss://dominio/23")
            assert json.loads(domain_table.contents[0].text)["tabela"] == "23"
            healthplan_profile = await session.read_resource("tiss://operadoras/005711")
            assert json.loads(healthplan_profile.contents[0].text) == operadoras.perfil("005711")
            simulated_rules = await session.read_resource("tiss://regras/000000")
            assert json.loads(simulated_rules.contents[0].text) == json.loads(
                (ROOT / "src/voa_tiss/rules/000000.json").read_text()
            )
            templates = await session.list_resource_templates()
            assert [item.uriTemplate for item in templates.resourceTemplates] == [
                "tiss://tuss/{tabela}/{pagina}",
                "tiss://dominio/{tabela}",
                "tiss://operadoras/{registro_ans}",
                "tiss://regras/{registro_ans}",
            ]
            prompts = await session.list_prompts()
            assert {prompt.name for prompt in prompts.prompts} == {
                "montar_lote",
                "corrigir_lote_rejeitado",
                "tratar_demonstrativo",
            }
            prompt = await session.get_prompt("montar_lote", {"atendimentos": "x"})
            prompt_text = prompt.messages[0].content.text
            assert "tiss_validate" in prompt_text and "tiss_apply_fixes" in prompt_text
            assert "Operadora: não informado" in prompt_text
            with pytest.raises(McpError):
                await session.get_prompt("montar_lote", {})
            with pytest.raises(McpError):
                await session.get_prompt("inexistente", {})
            lote = json.loads(
                (ROOT / "tests/fixtures/lotes/corrigivel-valor-divergente.json").read_text()
            )
            for _ in range(2):
                checked = await session.call_tool("tiss_validate", {"lote": lote})
                report = checked.structuredContent
                if report["valid"] and not report["findings"]:
                    break
                fixed = await session.call_tool(
                    "tiss_apply_fixes", {"lote": lote, "report": report}
                )
                assert fixed.isError is False
                lote = fixed.structuredContent["lote"]
            assert report["valid"] and not report["findings"]
            readme_resource = await session.read_resource("tiss://docs/readme")
            assert readme_resource.contents[0].text
            api_resource = await session.read_resource("tiss://docs/api")
            assert "sandbox_enviar_lote" in api_resource.contents[0].text
            assert "## Prompts MCP" in api_resource.contents[0].text
            assert "## Resources MCP" in api_resource.contents[0].text
            assert "tiss://regras/{registro_ans}" in api_resource.contents[0].text
            assert "tiss://schemas/lote" in api_resource.contents[0].text

    return run


@pytest.fixture
def healthplan_rules():
    path = ROOT / "tests/fixtures/rules/000000.json"
    package = json.loads(path.read_text(encoding="utf-8"))

    def replace(node):
        if isinstance(node, dict):
            return {key: replace(value) for key, value in node.items()}
        if isinstance(node, list):
            return [replace(value) for value in node]
        if isinstance(node, str):
            return node.replace("__REGISTRO_ANS__", "419761").replace("__NUMERO_LOTE__", "0007")
        return node

    return replace(package)


def xml_bytes(root: etree._Element) -> bytes:
    return etree.tostring(root, encoding="utf-8")


def mutate(change: Callable[[etree._Element], object]) -> bytes:
    root = etree.fromstring(examples.load("lote-valido"), parser())
    change(root)
    return xml_bytes(root)


def set_text(root: etree._Element, path: str, value: str) -> None:
    node = root.find(path, ANS)
    if node is None:
        raise ValueError(f"Elemento ausente: {path}")
    node.text = value


def remove_element(root: etree._Element, path: str) -> None:
    node = root.find(path, ANS)
    if node is None or node.getparent() is None:
        raise ValueError(f"Elemento ausente: {path}")
    node.getparent().remove(node)


@pytest.fixture
def xsd_cases() -> dict[str, bytes]:
    mutations: dict[str, Callable[[etree._Element], object]] = {
        "xsd.atributo": lambda root: root.set("extra", "x"),
        "xsd.elemento_inesperado": lambda root: etree.SubElement(
            root.find("ans:cabecalho", ANS), f"{{{NS}}}inesperado"
        ),
        "xsd.elemento_ausente": lambda root: remove_element(root, ".//ans:profissionalSolicitante"),
        "xsd.padrao": lambda root: set_text(root, ".//ans:CNPJ", "0000000000000X"),
        "xsd.enumeracao": lambda root: set_text(root, ".//ans:caraterAtendimento", "X"),
        "xsd.tamanho": lambda root: set_text(root, ".//ans:numeroCarteira", "X" * 21),
        "xsd.tipo": lambda root: set_text(root, ".//ans:dataExecucao", "2026-99-99"),
        "xsd.outro": lambda root: root.set(
            "{http://www.w3.org/2001/XMLSchema-instance}type", "UnknownType"
        ),
    }
    return {code: mutate(change) for code, change in mutations.items()}


def parse_return(body: str) -> bytes:
    return (
        f'<ans:mensagemTISS xmlns:ans="{NS}"><ans:operadoraParaPrestador>'
        f"<ans:demonstrativoAnaliseConta>{body}</ans:demonstrativoAnaliseConta>"
        "</ans:operadoraParaPrestador></ans:mensagemTISS>"
    ).encode()


def return_guide(prestador: str, operadora: str, released: str, glosa: str, code: str = "") -> str:
    return (
        f"<ans:dadosGuia><ans:numeroGuiaPrestador>{prestador}</ans:numeroGuiaPrestador>"
        f"<ans:numeroGuiaOperadora>{operadora}</ans:numeroGuiaOperadora>"
        "<ans:procedimentos><ans:procedimento><ans:codigoProcedimento>10101012</ans:codigoProcedimento>"
        f"<ans:valorLiberado>{released}</ans:valorLiberado><ans:valorGlosa>{glosa}</ans:valorGlosa>"
        f"<ans:codigoGlosa>{code}</ans:codigoGlosa></ans:procedimento></ans:procedimentos></ans:dadosGuia>"
    )


@dataclass
class UserGuide:
    id: str
    numero_guia_prestador: str
    numero_guia_operadora: str
    status: str = "em_analise"
