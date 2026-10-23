"""Normalização de mensagens XSD e criação de achados."""

from __future__ import annotations

import re
from contextlib import suppress
from typing import Any

from lxml import etree

from ._report import Finding
from ._schema import compile_schema
from ._xml import local_name

NS = "http://www.ans.gov.br/padroes/tiss/schemas"

_NAMESPACE_RE = re.compile(r"\{[^}]+\}")


def _first(element: etree._Element, name: str) -> etree._Element | None:
    if local_name(element.tag) == name:
        return element
    return next((child for child in element.iter() if local_name(child.tag) == name), None)


def _text(element: etree._Element | None) -> str | None:
    return None if element is None else (element.text or "").strip()


def _guia_numero(guia: etree._Element) -> str:
    return _text(_first(guia, "numeroGuiaPrestador")) or "?"


def _canonical_xpath(element: etree._Element) -> str:
    parts: list[str] = []
    current: etree._Element | None = element
    while current is not None:
        if not isinstance(current.tag, str):
            current = current.getparent()
            continue
        qname = etree.QName(current)
        step = (
            f"ans:{qname.localname}"
            if qname.namespace == NS
            else f"*[local-name()='{qname.localname}']"
        )
        parent = current.getparent()
        if parent is not None:
            same = [
                child
                for child in parent
                if isinstance(child.tag, str)
                and etree.QName(child).localname == qname.localname
                and etree.QName(child).namespace == qname.namespace
            ]
            if len(same) > 1:
                step += f"[{same.index(current) + 1}]"
        parts.append(step)
        current = parent
    return "/" + "/".join(reversed(parts))


def _xpath_guia(element: etree._Element, guias: list[etree._Element]) -> str | None:
    current: etree._Element | None = element
    while current is not None:
        for guia in guias:
            if current is guia:
                return _guia_numero(current)
        current = current.getparent()
    return None


def _compiled_schema(version: str) -> etree.XMLSchema:
    return compile_schema(version)


def _expected_names(message: str) -> list[str]:
    match = re.search(r"Expected is \((.*?)\)", message)
    if not match:
        return []
    return [
        _NAMESPACE_RE.sub("", part.strip().strip("'\"")).rsplit(":", 1)[-1]
        for part in match.group(1).split(",")
    ]


def _message_element(message: str) -> str | None:
    match = re.search(r"Element ['\"]([^'\"]+)['\"]", _NAMESPACE_RE.sub("", message))
    if match:
        return match.group(1).rsplit(":", 1)[-1]
    return None


def _path_parent(path: str | None) -> str | None:
    if not path or "/" not in path.rstrip("/"):
        return None
    parent = path.rstrip("/").rsplit("/", 1)[0].rsplit("/", 1)[-1]
    parent = re.sub(r"\[.*\]$", "", parent)
    return parent.rsplit(":", 1)[-1] or None


def _message_value(message: str) -> str | None:
    sanitized = _NAMESPACE_RE.sub("", message)
    body_match = re.search(r"Element ['\"]([^'\"]+)['\"]:\s*(.*)", sanitized)
    body = body_match.group(2) if body_match else sanitized
    match = re.search(r"(?:the )?value ['\"]([^'\"]*)['\"]", body, re.I)
    if match:
        return match.group(1)
    match = re.match(r"['\"]([^'\"]*)['\"]", body)
    return match.group(1) if match else None


def _xsd_code(entry: Any) -> str:
    name = entry.type_name.upper()
    message = entry.message
    if name == "SCHEMAV_CVC_ELT_1" or (
        name == "SCHEMAV_ELEMENT_CONTENT" and "not expected" in message
    ):
        return "xsd.elemento_inesperado"
    if name == "SCHEMAV_ELEMENT_CONTENT" and "Missing child element(s)" in message:
        return "xsd.elemento_ausente"
    if name in {"SCHEMAV_CVC_COMPLEX_TYPE_3_2_1", "SCHEMAV_CVC_COMPLEX_TYPE_3_2_2"}:
        return "xsd.atributo"
    if "PATTERN" in name:
        return "xsd.padrao"
    if "ENUMERATION" in name:
        return "xsd.enumeracao"
    if any(
        part in name
        for part in ("LENGTH", "MINLENGTH", "MAXLENGTH", "TOTALDIGITS", "FRACTIONDIGITS")
    ):
        return "xsd.tamanho"
    if any(
        part in name for part in ("MININCLUSIVE", "MAXINCLUSIVE", "MINEXCLUSIVE", "MAXEXCLUSIVE")
    ):
        return "xsd.outro"
    if "ATTRIBUTE" in name or "ATTR" in name:
        return "xsd.atributo"
    if any(part in name for part in ("DATATYPE_VALID", "CVC_TYPE", "SIMPLE_TYPE")):
        return "xsd.tipo"
    return "xsd.outro"


def _xsd_message(entry: Any) -> tuple[str, list[str] | None]:
    message = _NAMESPACE_RE.sub("", entry.message).strip()
    code = _xsd_code(entry)
    expected = _expected_names(entry.message)
    element = _message_element(entry.message)
    value = _message_value(entry.message)
    if code == "xsd.elemento_inesperado":
        actual = f"Elemento {element or 'XML'} inesperado"
        parent = _path_parent(entry.path)
        if parent:
            actual += f" em {parent}"
        if expected:
            actual += f"; esperado: {', '.join(expected)}"
        return actual + ".", expected or None
    if code == "xsd.elemento_ausente":
        parent = element or "XML"
        if expected:
            return f"Falta elemento em {parent}; esperado: {', '.join(expected)}.", expected
        return f"Falta elemento em {parent}.", None
    if code == "xsd.padrao" and element and value is not None:
        return f"Valor '{value}' não corresponde ao padrão do elemento {element}.", None
    if code == "xsd.enumeracao" and element and value is not None:
        return f"Valor '{value}' não pertence à enumeração do elemento {element}.", None
    if code == "xsd.tamanho" and element:
        if value is not None:
            return f"Tamanho inválido no elemento {element} para o valor '{value}'.", None
        length = re.search(r"length of ['\"](\d+)['\"]", message)
        if length:
            return f"Tamanho inválido no elemento {element}: {length.group(1)} caracteres.", None
    if code == "xsd.tipo" and element and value is not None:
        return f"Valor '{value}' inválido para o tipo do elemento {element}.", None
    return "XSD: " + message, None


def _xsd_findings(
    doc: etree._ElementTree,
    root: etree._Element,
    guias: list[etree._Element],
    version: str,
) -> list[Finding]:
    schema = _compiled_schema(version)
    schema.validate(doc)
    namespaces = {key: value for key, value in root.nsmap.items() if key and value}
    namespaces.setdefault("ans", NS)
    findings: list[Finding] = []
    for entry in schema.error_log:
        code = _xsd_code(entry)
        message, needs = _xsd_message(entry)
        resolved: list[Any] = []
        if entry.path:
            with suppress(etree.XPathError):
                resolved = doc.xpath(entry.path, namespaces=namespaces)
        element = (
            resolved[0] if len(resolved) == 1 and isinstance(resolved[0], etree._Element) else None
        )
        findings.append(
            Finding(
                code=code,
                severity="error",
                guia=_xpath_guia(element, guias) if element is not None else None,
                xpath=_canonical_xpath(element) if element is not None else entry.path,
                pointer=None,
                message=message,
                fix=None,
                needs=needs,
            )
        )
    return findings
