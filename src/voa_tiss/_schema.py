"""Verificação local dos esquemas de comunicação da ANS."""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from pathlib import Path

from lxml import etree

PINNED_PROVENANCE = {
    "4.03.00": "656fce617c0274056a7a4de46d54f4fc82a40fa8bc0e2fe610af0e8004b8ac77",
    "4.02.00": "f0dd9bcb0c00636cfec1dfe11cfab1858e40c49c80b7a7ed915abb2fcdde3f2f",
}
NS = "http://www.ans.gov.br/padroes/tiss/schemas"
_XS = "{http://www.w3.org/2001/XMLSchema}"


class SchemaBundleError(ValueError):
    """Erro em um pacote XSD inválido ou não suportado."""


def schema_dir(version: str) -> Path:
    """Retorna o diretório local dos XSDs da versão."""
    if version not in PINNED_PROVENANCE:
        raise SchemaBundleError(f"Versão TISS não empacotada: {version}")
    root = files(__package__) / "_data" / "schemas" / version
    if not isinstance(root, Path):
        raise SchemaBundleError(
            "Os XSDs empacotados precisam estar disponíveis em arquivos locais."
        )
    return root


def compile_schema(version: str) -> etree.XMLSchema:
    """Verifica o pacote e compila o XSD raiz sem rede."""
    root = verify_schema_bundle(schema_dir(version), expected_version=version)
    return etree.XMLSchema(etree.parse(str(root), parser()))


def parser() -> etree.XMLParser:
    """Cria um parser XML sem rede nem entidades externas."""
    return etree.XMLParser(no_network=True, load_dtd=False, resolve_entities=False)


def verify_schema_bundle(directory: str | Path, *, expected_version: str) -> Path:
    """Verifica o pacote XSD e suas dependências."""
    directory = Path(directory)
    expected_hash = PINNED_PROVENANCE.get(expected_version)
    if expected_hash is None:
        raise SchemaBundleError(f"Versão TISS não empacotada: {expected_version}")
    try:
        raw = (directory / "provenance.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_hash:
            raise SchemaBundleError("Proveniência XSD divergente do pacote verificado")
        provenance = json.loads(raw)
        if provenance["version"] != expected_version:
            raise SchemaBundleError("Versão XSD divergente da configuração da operadora")
        files = provenance["files"]
        if {p.name for p in directory.iterdir()} != {*files, "provenance.json"}:
            raise SchemaBundleError("Conjunto de arquivos XSD incompleto ou inesperado")
        for name, digest in files.items():
            path = directory / name
            if path.is_symlink() or path.name != name:
                raise SchemaBundleError(f"Caminho XSD inválido: {name}")
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise SchemaBundleError(f"Hash XSD divergente: {name}")
            doc = etree.parse(str(path), parser())
            for node in doc.iter():
                if node.tag not in {_XS + "include", _XS + "import", _XS + "redefine"}:
                    continue
                location = node.get("schemaLocation")
                if not location or location not in files or Path(location).name != location:
                    raise SchemaBundleError(f"Dependência XSD não empacotada: {location}")
        root_name = provenance["root"]
        if not isinstance(root_name, str) or root_name not in files:
            raise SchemaBundleError("XSD raiz não pertence ao pacote")
        root = directory / root_name
        etree.XMLSchema(etree.parse(str(root), parser()))
        return root
    except (OSError, KeyError, ValueError, etree.LxmlError) as exc:
        if isinstance(exc, SchemaBundleError):
            raise
        raise SchemaBundleError(f"Pacote XSD indisponível ou inválido: {exc}") from exc
