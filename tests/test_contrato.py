from __future__ import annotations

import builtins
import datetime
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from decimal import Decimal

import jsonschema
import pytest
from conftest import ROOT

import voa_tiss
from bench._tarefas import TASK_DIR, gerar
from bench._verificar import verificar
from scripts import manutencao
from voa_tiss import MissingExtraError, examples, render_sadt, sadt_catalog, sadt_missing
from voa_tiss._sadt import load_bundle, render_html
from voa_tiss._schema import (
    PINNED_PROVENANCE,
    SchemaBundleError,
    schema_dir,
    verify_schema_bundle,
)
from voa_tiss.codes import CODES


def test_public_api_and_example_contract():
    assert set(voa_tiss.__all__) == {
        "AuditContext",
        "AutorizacaoError",
        "BundleError",
        "Decision",
        "Decisao",
        "Finding",
        "Lote",
        "LoteError",
        "MissingExtraError",
        "Proposta",
        "Reconciliacao",
        "Report",
        "RetornoError",
        "PatchError",
        "apply_fixes",
        "audit",
        "build_lote",
        "build_autorizacao",
        "check",
        "check_autorizacao",
        "hash_epilogo",
        "glosa",
        "examples",
        "json_schema",
        "parse_lote",
        "parse_demonstrativo",
        "parse_autorizacao",
        "plan_reconciliation",
        "render_sadt",
        "sadt_catalog",
        "sadt_missing",
        "dominio",
        "operadoras",
        "validate",
        "validate_package",
    }
    assert set(voa_tiss.json_schema("finding")["properties"]["code"]["enum"]) == set(CODES)
    assert voa_tiss.examples.names() == [
        "lote-valido",
        "lote-com-erros",
        "demonstrativo",
        "autorizacao-solicitacao",
        "autorizacao-resposta",
    ]
    with pytest.raises(ValueError):
        voa_tiss.examples.load("../unknown")
    request = json.loads((ROOT / "tests/fixtures/autorizacao-solicitacao.json").read_text())
    authorization_xml = voa_tiss.build_autorizacao(request)
    with pytest.raises(voa_tiss.AutorizacaoError):
        voa_tiss.build_autorizacao({**request, "solicitacao": None, "autorizacao": {}})
    with pytest.raises(voa_tiss.AutorizacaoError):
        voa_tiss.build_autorizacao(
            {key: value for key, value in request.items() if key != "solicitacao"}
        )
    with pytest.raises(voa_tiss.AutorizacaoError):
        voa_tiss.build_autorizacao(
            {
                **request,
                "solicitacao": {**request["solicitacao"], "campo_desconhecido": "x"},
            }
        )
    with pytest.raises(voa_tiss.AutorizacaoError):
        voa_tiss.parse_autorizacao(
            authorization_xml.replace(b"SOLICITACAO_PROCEDIMENTOS", b"TIPO_INVALIDO")
        )


def test_generated_artifacts_and_golden_report_are_current():
    assert manutencao._write_artifacts(check=True)
    expected = (ROOT / "tests/golden/lote-com-erros.report.json").read_text().strip()
    assert voa_tiss.validate(voa_tiss.examples.load("lote-com-erros")).to_json() == expected


@pytest.mark.parametrize("change", ["missing", "tampered", "extra", "provenance", "symlink"])
def test_xsd_bundle_rejects_changed_members(tmp_path, change):
    target = tmp_path / "bundle"
    shutil.copytree(schema_dir("4.03.00"), target)
    member = target / "tissGuiasV4_03_00.xsd"
    if change == "missing":
        member.unlink()
    elif change == "tampered":
        member.write_bytes(member.read_bytes() + b"\n")
    elif change == "extra":
        (target / "unexpected.xsd").write_text("x")
    elif change == "provenance":
        (target / "provenance.json").write_text("{}")
    else:
        member.unlink()
        member.symlink_to(schema_dir("4.03.00") / member.name)
    with pytest.raises(SchemaBundleError):
        verify_schema_bundle(target, expected_version="4.03.00")


@pytest.mark.parametrize(
    "location", ["https://example.invalid/a.xsd", "../a.xsd", "missing.xsd", ""]
)
def test_xsd_bundle_rejects_unclosed_imports(tmp_path, monkeypatch, location):
    target = tmp_path / "bundle"
    shutil.copytree(schema_dir("4.03.00"), target)
    manifest_path = target / "provenance.json"
    manifest = json.loads(manifest_path.read_text())
    root = target / manifest["root"]
    raw = root.read_bytes().replace(
        b'schemaLocation="tissSimpleTypesV4_03_00.xsd"',
        f'schemaLocation="{location}"'.encode(),
    )
    root.write_bytes(raw)
    manifest["files"][root.name] = hashlib.sha256(raw).hexdigest()
    pinned = json.dumps(manifest).encode()
    manifest_path.write_bytes(pinned)
    monkeypatch.setitem(PINNED_PROVENANCE, "4.03.00", hashlib.sha256(pinned).hexdigest())
    with pytest.raises(SchemaBundleError, match="Dependência XSD"):
        verify_schema_bundle(target, expected_version="4.03.00")


def test_report_schema_and_determinism():
    reports = [
        voa_tiss.validate(examples.load("lote-valido")),
        voa_tiss.validate(examples.load("lote-com-erros")),
        voa_tiss.validate((ROOT / "tests/fixtures/xml/malformed.xml").read_bytes()),
    ]
    validator = jsonschema.Draft202012Validator(voa_tiss.json_schema("report"))
    for report in reports:
        validator.validate(report.to_dict())
        assert json.loads(report.to_json()) == report.to_dict()
    code = (
        "from voa_tiss import examples,validate;"
        "print(validate(examples.load('lote-com-erros')).to_json())"
    )
    outputs = []
    for seed in ("1", "2"):
        env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT / "src")}
        outputs.append(subprocess.check_output([sys.executable, "-c", code], cwd=ROOT, env=env))
    assert outputs[0] == outputs[1] == (reports[1].to_json() + "\n").encode()


def test_public_apis_are_offline(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    assert voa_tiss.validate(examples.load("lote-valido")).valid
    assert voa_tiss.parse_demonstrativo(examples.load("demonstrativo"))
    from voa_tiss.tuss import lookup, search

    assert lookup("10101012", tabela="22")
    assert search("consultorio")
    assert voa_tiss.sadt_catalog()
    assert isinstance(voa_tiss.sadt_missing({}), list)


def test_sadt_catalog_completeness_and_optional_dependencies(monkeypatch, tmp_path):
    original_import = builtins.__import__

    def without_pdf(name, *args, **kwargs):
        if name.split(".", 1)[0] in {"weasyprint", "jinja2", "markupsafe"}:
            raise ImportError(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_pdf)
    assert sadt_catalog()["fields"]
    assert isinstance(sadt_missing({}), list)
    with pytest.raises(MissingExtraError, match="voa-tiss\\[pdf\\]"):
        render_sadt({}, tmp_path / "guide.pdf")


def test_complete_guide_and_line_totals_and_html():
    complete = {
        "registro_ans": "123456",
        "numero_guia_prestador": "G-1",
        "beneficiario_carteira": "0001",
        "beneficiario_nome": "PACIENTE EXEMPLO",
        "atendimento_rn": "N",
        "solicitante_codigo_operadora": "0001",
        "solicitante_nome_contratado": "CLINICA EXEMPLO",
        "solicitante_conselho": "CRM",
        "solicitante_numero_conselho": "12345",
        "solicitante_uf_conselho": "SP",
        "solicitante_cbo": "225125",
        "carater_atendimento": "1",
        "procedimentos_solicitados": [
            {
                "tabela": "22",
                "codigo": "40901220",
                "descricao": "Hemograma",
                "quantidade_solicitada": "1",
            }
        ],
    }
    assert sadt_missing(complete) == []

    from voa_tiss._line_total import LineTotalError, line_total, line_total_cents

    assert line_total(unit_price="12.50", quantity=2) == Decimal("25.00")
    assert line_total_cents(unit_price_cents=7, quantity=3, factor="0.5") == Decimal("10.5")
    with pytest.raises(LineTotalError):
        line_total(unit_price="12.50", quantity=0)
    html = render_html({"beneficiario_nome": "<script>injection</script>"}, load_bundle())
    assert "&lt;script&gt;" in html and "<script>injection</script>" not in html


def test_sadt_pdf_render_when_available(tmp_path):
    pytest.importorskip("weasyprint")
    output = tmp_path / "guide.pdf"
    render_sadt({}, output, gen_date=datetime.date(2026, 6, 22))
    assert output.is_file() and output.stat().st_size > 0


@pytest.mark.parametrize("task", gerar(), ids=lambda task: task["id"])
def test_benchmark_task_contract(task):
    path = TASK_DIR / f"{task['id']}.json"
    assert json.loads(path.read_text(encoding="utf-8")) == task
    assert verificar(task, task["referencia"])[0]
    assert not verificar(task, task["errada"])[0]
