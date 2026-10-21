"""Validação XML, XSD e regras do lote TISS."""

from __future__ import annotations

import io
import re
from contextlib import suppress
from decimal import Decimal, InvalidOperation
from typing import Any

from lxml import etree

from ._lote_codec import parse_lote
from ._report import Finding, Report
from ._rules import rule_findings
from ._schema import parser
from ._validate_xsd import _canonical_xpath, _first, _guia_numero, _text, _xsd_findings
from ._xml import local_name
from .codes import CODE_CATALOG

SUPPORTED_VERSIONS = {"4.02.00", "4.03.00"}

_ALLOWED_CONTROL = {0x09, 0x0A, 0x0D}
_ENCODING_RE = re.compile(rb"""<\?xml[^>]*encoding\s*=\s*['"]([^'"]+)['"]""", re.I)


def _decimal(element: etree._Element | None) -> Decimal | None:
    raw = _text(element)
    if not raw:
        return None
    if "," in raw and "." not in raw:
        raw = raw.replace(",", ".")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _guia_elements(root: etree._Element) -> list[etree._Element]:
    candidates = [
        element
        for element in root.iter()
        if local_name(element.tag).lower().startswith("guia")
        and any(
            local_name(descendant.tag) == "numeroGuiaPrestador" for descendant in element.iter()
        )
    ]
    identities = {id(element) for element in candidates}
    return [
        element
        for element in candidates
        if not any(
            id(descendant) in identities
            for descendant in element.iter()
            if descendant is not element
        )
    ]


def _items(guia: etree._Element) -> list[etree._Element]:
    return [
        element
        for element in guia.iter()
        if any(local_name(child.tag) == "sequencialItem" for child in element)
    ]


def _finding(
    code: str,
    message: str,
    *,
    severity: str | None = None,
    guia: str | None = None,
    element: etree._Element | None = None,
    needs: list[str] | None = None,
) -> Finding:
    spec = CODE_CATALOG[code]
    severity = severity or spec["severity"]
    if needs is None and spec["needs"] == "pointer":
        needs = ["/contexto"]
    return Finding(
        code=code,
        severity=severity,  # type: ignore[arg-type]
        guia=guia,
        xpath=_canonical_xpath(element) if element is not None else None,
        pointer=None,
        message=message,
        fix=None,
        needs=needs,
        glosa=spec["glosa"],
    )


def _decode_xml(xml: str | bytes) -> tuple[bytes, str | None]:
    if isinstance(xml, str):
        declaration = re.search(r"""<\?xml[^>]*encoding\s*=\s*['"]([^'"]+)['"]""", xml, re.I)
        encoding = declaration.group(1) if declaration else "utf-8"
        try:
            raw = xml.encode(encoding)
            text = raw.decode(encoding)
        except (LookupError, UnicodeEncodeError, UnicodeDecodeError):
            return b"", "O XML contém caracteres incompatíveis com a codificação declarada."
    elif isinstance(xml, bytes):
        declared = _ENCODING_RE.search(xml[:512])
        encoding = declared.group(1).decode("ascii", "replace") if declared else "utf-8"
        try:
            text = xml.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            return b"", "Os bytes do XML não correspondem à codificação declarada."
        raw = xml
    else:
        raise TypeError("xml deve ser str ou bytes")
    invalid = sorted(
        {
            ord(character)
            for character in text
            if (ord(character) < 0x20 and ord(character) not in _ALLOWED_CONTROL)
            or ord(character) == 0x7F
        }
    )
    if invalid:
        codes = ", ".join(f"0x{code:02X}" for code in invalid)
        return raw, f"Caracteres de controle inválidos no XML: {codes}."
    return raw, None


def _rule_findings(root: etree._Element, guias: list[etree._Element]) -> list[Finding]:
    findings: list[Finding] = []
    seen: dict[str, int] = {}
    duplicate_reported: set[str] = set()
    for guia in guias:
        number = _guia_numero(guia)
        seen[number] = seen.get(number, 0) + 1
        if seen[number] > 1 and number != "?" and number not in duplicate_reported:
            duplicate_reported.add(number)
            findings.append(
                _finding(
                    "lote.guia_duplicada",
                    f"numeroGuiaPrestador {number!r} aparece mais de uma vez no lote.",
                    guia=number,
                    element=guia,
                )
            )

    total_items = Decimal(0)
    any_item = False
    guide_sums: list[tuple[etree._Element, Decimal]] = []
    for guia in guias:
        number = _guia_numero(guia)
        items = _items(guia)
        any_item = any_item or bool(items)
        guide_sum = Decimal(0)
        sequences: list[int] = []
        for item in items:
            raw = _text(_first(item, "sequencialItem"))
            try:
                sequences.append(int(raw or ""))
            except ValueError:
                sequences = []
                break
        if items and sorted(sequences) != list(range(1, len(items) + 1)):
            findings.append(
                _finding(
                    "guia.sequencial",
                    f"Sequenciais dos itens da guia {number} devem ser contínuos a partir de 1.",
                    guia=number,
                    element=guia,
                )
            )

        for item in items:
            total_element = _first(item, "valorTotal")
            total = _decimal(total_element)
            unit = _decimal(_first(item, "valorUnitario"))
            quantity = _decimal(_first(item, "quantidadeExecutada"))
            if total is None or total == 0:
                findings.append(
                    _finding(
                        "item.valor_zerado",
                        f"valorTotal ausente ou zerado no item da guia {number}.",
                        guia=number,
                        element=item,
                        needs=["valorTotal"],
                    )
                )
                continue
            guide_sum += total
            total_items += total
            if (
                unit is not None
                and quantity is not None
                and abs(unit * quantity - total) > Decimal("0.01")
            ):
                findings.append(
                    _finding(
                        "item.valor_divergente",
                        f"valorTotal {total:.2f} diverge de valorUnitario × quantidade.",
                        guia=number,
                        element=total_element,
                    )
                )
        guide_sums.append((guia, guide_sum))

        if not _text(_first(guia, "numeroCarteira")):
            findings.append(
                _finding(
                    "guia.carteirinha_ausente",
                    f"numeroCarteira ausente na guia {number}.",
                    severity="warning",
                    guia=number,
                    element=guia,
                    needs=["numeroCarteira"],
                )
            )
        if items:
            has_professional = any(
                local_name(element.tag)
                in {
                    "conselhoProfissional",
                    "numeroConselhoProfissional",
                    "CBOS",
                    "cbos",
                    "siglaConselho",
                }
                and (element.text or "").strip()
                for element in guia.iter()
            )
            if not has_professional:
                findings.append(
                    _finding(
                        "guia.executante_ausente",
                        f"Dados de conselho e CBO do executante ausentes na guia {number}.",
                        severity="warning",
                        guia=number,
                        element=guia,
                        needs=[
                            "conselhoProfissional",
                            "numeroConselhoProfissional",
                            "CBOS",
                        ],
                    )
                )

    guide_total_elements = [
        (guia, guide_sum, _first(guia, "valorTotalGeral"))
        for guia, guide_sum in guide_sums
        if _first(guia, "valorTotalGeral") is not None
    ]
    if guide_total_elements:
        for _, guide_sum, declared_element in guide_total_elements:
            declared = _decimal(declared_element)
            if any_item and declared is not None and abs(declared - guide_sum) > Decimal("0.01"):
                findings.append(
                    _finding(
                        "lote.valor_total_geral",
                        f"valorTotalGeral {declared:.2f} diverge da soma "
                        f"dos itens {guide_sum:.2f}.",
                        element=declared_element,
                    )
                )
    else:
        declared_element = _first(root, "valorTotalGeral")
        declared = _decimal(declared_element)
        if any_item and declared is not None and abs(declared - total_items) > Decimal("0.01"):
            findings.append(
                _finding(
                    "lote.valor_total_geral",
                    f"valorTotalGeral {declared:.2f} diverge da soma dos itens {total_items:.2f}.",
                    element=declared_element,
                )
            )
    return findings


def validate(xml: bytes | str, *, version: str | None = None, operadora: Any = None) -> Report:
    """Valida XML TISS e retorna os achados."""
    raw, encoding_error = _decode_xml(xml)
    if encoding_error:
        return Report(False, None, (_finding("xml.encoding", encoding_error),))
    try:
        doc = etree.parse(io.BytesIO(raw), parser())
    except (etree.XMLSyntaxError, OSError) as exc:
        error = exc.error_log.last_error if isinstance(exc, etree.XMLSyntaxError) else None
        location = f" (linha {error.line}, coluna {error.column})" if error is not None else ""
        return Report(
            False,
            None,
            (_finding("xml.malformado", f"XML malformado{location}."),),
        )
    if doc.docinfo.doctype:
        return Report(False, None, (_finding("xml.doctype", "DOCTYPE não é permitido."),))

    root = doc.getroot()
    detected_element = next(
        (element for element in root.iter() if local_name(element.tag) == "Padrao"), None
    )
    detected = _text(detected_element)
    findings: list[Finding] = []
    chosen = version
    if version is not None and detected is not None and version != detected:
        findings.append(
            _finding(
                "versao.divergente",
                f"Versão informada {version} difere da versão XML {detected}.",
            )
        )
    elif version is None:
        chosen = detected
    if chosen is None:
        findings.append(
            _finding("versao.nao_detectada", "Não foi possível detectar a versão TISS no XML.")
        )
    elif chosen not in SUPPORTED_VERSIONS:
        findings.append(
            _finding(
                "versao.nao_suportada",
                f"Versão TISS {chosen} não está incluída neste pacote.",
            )
        )
        chosen = None

    guias = _guia_elements(root)
    if chosen is not None:
        findings.extend(_xsd_findings(doc, root, guias, chosen))
    if chosen == "4.03.00" and operadora is not None:
        with suppress(ValueError):
            findings.extend(rule_findings(dict(parse_lote(raw)), operadora))
    findings.extend(_rule_findings(root, guias))
    valid = not any(finding.severity == "error" for finding in findings)
    return Report(valid, chosen, tuple(findings))


__all__ = ["validate"]
