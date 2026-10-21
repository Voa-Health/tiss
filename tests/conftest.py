from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
from lxml import etree

from voa_tiss import examples, parse_lote
from voa_tiss._schema import parser

ROOT = Path(__file__).resolve().parents[1]
NS = "http://www.ans.gov.br/padroes/tiss/schemas"
ANS = {"ans": NS}


@pytest.fixture
def valid_lote():
    return parse_lote(examples.load("lote-valido"))


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
