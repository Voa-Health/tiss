from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
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
from voa_tiss.server._ops import OPS

ROOT = Path(__file__).resolve().parents[1]
NS = "http://www.ans.gov.br/padroes/tiss/schemas"
ANS = {"ans": NS}
TUSS_PAGE_SIZE = 200


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
            operator_resource = await session.read_resource("tiss://operadoras")
            assert json.loads(operator_resource.contents[0].text) == operadoras.info()
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
            operator_profile = await session.read_resource("tiss://operadoras/005711")
            assert json.loads(operator_profile.contents[0].text) == operadoras.perfil("005711")
            with pytest.raises(McpError):
                await session.read_resource("tiss://regras/000000")
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
def operator_rules():
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
