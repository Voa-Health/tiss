from __future__ import annotations

import datetime
import hashlib
import json
from typing import ClassVar

import pytest
from conftest import ROOT

from scripts import _manutencao_glosa, manutencao
from tiss import dominio, glosa, operadoras
from tiss._schema import (
    PINNED_PROVENANCE,
    compile_schema,
    schema_dir,
    verify_schema_bundle,
)
from tiss.codes import CODE_CATALOG
from tiss.tuss import info, lookup, search, tables
from tiss.tuss._index import TussIndex, content_tokens, fold, is_vigente


def test_tuss_lookup_search_and_copy_contract():
    assert info()["records"] == 68_022
    assert {row["tabela"] for row in tables()} == {"18", "19", "20", "22"}
    assert lookup("10101012", tabela="22")
    assert search("ressonância magnética", tabela="22")
    row = lookup("10101012", tabela="22")[0]
    row["codigo"] = "changed"
    assert lookup("10101012", tabela="22")[0]["codigo"] == "10101012"
    with pytest.raises(ValueError, match="tabelas disponíveis"):
        lookup("1", tabela="unknown")
    with pytest.raises(ValueError):
        search("")


def test_tuss_bake_and_index_are_deterministic(tmp_path):
    fixtures = ROOT / "tests/fixtures"
    tables = {name: fixtures / f"tuss_curated_t{name}.csv" for name in ("18", "19", "20", "22")}
    baked = tmp_path / "baked.json"
    arguments = ["tuss", "--out", str(baked)]
    arguments.extend(f"--table={table}={path}" for table, path in tables.items())
    assert manutencao.main(arguments) == 0
    assert baked.read_bytes() == (fixtures / "tuss_curated.json").read_bytes()

    dataset = json.loads(baked.read_text(encoding="utf-8"))
    index = TussIndex(dataset["records"], tables=dataset["tables"])
    assert index.get("10101012", tabela="22")
    assert index.lookup("consulta em consultorio", today=datetime.date(2026, 6, 22))
    assert fold("Consultório") == "consultorio"
    assert content_tokens("ressonância magnética do crânio") == {"rm", "cranio"}
    assert not is_vigente({"vigencia_fim": "2015-12-31"}, "2026-01-01")
    dated = TussIndex(
        [{"tabela": "22", "codigo": "X1", "termo": "Exemplo", "vigencia_fim": "2020-01-01"}],
        tables={"22": "Procedimentos"},
    )
    assert not dated.get("X1", include_expired=False, today=datetime.date(2026, 1, 1))
    assert dated.get("X1", include_expired=True, today=datetime.date(2026, 1, 1))

    notebook = json.loads((ROOT / "docs/tutoriais/01-validar-um-lote.ipynb").read_text())
    output = "".join(notebook["cells"][1]["outputs"][0]["data"]["text/plain"]).rstrip("\n")
    destination = tmp_path / "tutoriais"

    assert manutencao.main(["gitbook", str(destination)]) == 0
    pages = sorted(destination.glob("*.md"))
    assert len(pages) == 9
    first_page = (destination / "01-validar-um-lote.md").read_text()
    assert first_page.startswith(
        "---\ndescription: Comece pelo exemplo incluído. O relatório reúne achados que podem "
        "ser revisados antes de corrigir a guia.\n---"
    )
    colab_url = (
        "https://colab.research.google.com/github/Voa-Health/tiss/blob/main/docs/tutoriais/"
        "01-validar-um-lote.ipynb"
    )
    assert colab_url in first_page
    assert f"```text\n{output}\n```" in first_page
    first_run = {page.name: page.read_bytes() for page in pages}

    assert manutencao.main(["gitbook", str(destination)]) == 0
    assert {page.name: page.read_bytes() for page in pages} == first_run


def test_packaged_data_and_catalog_glosas():
    assert dominio.lookup("38", "1801")[0]["descricao"] == glosa("1801")["descricao"]
    assert len(dominio.tables()) >= 14
    assert operadoras.lookup("419761")["registro_ans"] == "419761"
    bradesco = {row["periodo"]: row for row in operadoras.perfil("005711")["indicadores"]["serie"]}
    assert bradesco["2025-01"]["glosa_inicial"] == 19.47
    assert "glosa_inicial" not in bradesco["2025-01"]["inconsistentes"]
    assert bradesco["2025-02"]["glosa_inicial"] == 99.06
    assert "glosa_inicial" in bradesco["2025-02"]["inconsistentes"]
    assert not bradesco["2025-02"]["consistente"]
    assert "guias_sem_retorno" in bradesco["2022-02"]["inconsistentes"]
    assert "guias_sem_retorno" not in bradesco["2024-02"]["inconsistentes"]
    baixa = [{"guias_sem_retorno": valor, "inconsistentes": []} for valor in (0.2, 0.3, 2.0)]
    _manutencao_glosa._inconsistentes(baixa)
    assert not baixa[2]["inconsistentes"]
    ausente = operadoras.perfil("422681")["indicadores"]["serie"][6]
    assert (ausente["periodo"], ausente["glosa_inicial"]) == ("2024-01", None)
    assert "glosa_inicial" in ausente["inconsistentes"]
    assert operadoras.perfil("999999") is None
    expected = {
        "audit.procedimento_fora_da_tabela": "1801",
        "tuss.inexistente": "1801",
        "tuss.fora_de_vigencia": "1801",
        "audit.autorizacao_ausente": "1425",
        "audit.autorizacao_vencida": "1414",
        "audit.carteirinha_ausente": "1001",
        "guia.carteirinha_ausente": "1001",
        "regra.exige_autorizacao": "1818",
        "audit.carteirinha_vencida": "1017",
        "guia.executante_ausente": "1311",
        "guia.sequencial": "3167",
        "audit.data_ausente": "3226",
        "audit.operadora_divergente": "5027",
        "lote.hash_divergente": "5014",
        "versao.nao_suportada": "5028",
        "versao.divergente": "5028",
        "xml.malformado": "5002",
    }
    actual = {code: spec["glosa"] for code, spec in CODE_CATALOG.items() if spec["glosa"]}
    assert actual == expected
    assert all(glosa(code)["descricao"] for code in expected.values())


def test_xsd_data_provenance_and_compile():
    source = schema_dir("4.03.00")
    manifest = json.loads((source / "provenance.json").read_text())
    digest = hashlib.sha256((source / "provenance.json").read_bytes()).hexdigest()
    assert digest == PINNED_PROVENANCE["4.03.00"]
    assert manifest["archive_sha256"] == (
        "db8640e1c3b87085892f54f838bfcea9934439ff365798c8428559f88c13d62d"
    )
    assert len(manifest["files"]) == 7
    assert verify_schema_bundle(source, expected_version="4.03.00").name == manifest["root"]
    assert compile_schema("4.03.00")


def test_tuss_info_uses_shared_index_header(monkeypatch):
    from tiss import tuss

    class Index:
        size = 5
        metadata: ClassVar[dict[str, object]] = {
            "source": "bundle",
            "license": "CC BY-ND",
            "tables": {"22": "Procedimentos"},
        }

    monkeypatch.setattr(tuss, "get_default_index", Index)
    assert tuss.info() == {
        "source": "bundle",
        "license": "CC BY-ND",
        "records": 5,
        "tables": {"22": "Procedimentos"},
    }
