from __future__ import annotations

import builtins
import dataclasses
import datetime
import hashlib
import http.server
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import threading
import zlib
from decimal import Decimal

import jsonschema
import pytest
from conftest import ANS, ROOT
from lxml import etree
from pypdf import PdfReader

import tiss
from bench._tarefas import TASK_DIR, gerar
from bench._verificar import verificar
from scripts import manutencao
from tiss import MissingExtraError, examples, render_sadt, sadt_catalog, sadt_missing
from tiss.__main__ import main as cli_main
from tiss._rules import _package
from tiss._sadt import load_bundle, render_html
from tiss._schema import (
    PINNED_PROVENANCE,
    SchemaBundleError,
    parser,
    schema_dir,
    verify_schema_bundle,
)
from tiss.codes import CODES


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("lote-valido", set()),
        (
            "lote-com-erros",
            {
                "guia.sequencial",
                "item.valor_divergente",
                "item.valor_zerado",
                "lote.valor_total_geral",
            },
        ),
        ("guia-consulta", set()),
        ("hash-divergente", set()),
        ("hash-ausente", set()),
        ("autorizacao.aprovar-json", "aprovar_por_regra"),
        ("autorizacao.pendente-json", "pendente"),
        ("autorizacao.auditoria-xml", "encaminhar_auditor"),
        ("autorizacao.sem-regra-xml", "encaminhar_auditor"),
        ("autorizacao.carteirinha-json", "encaminhar_auditor"),
    ],
)
def test_example_reports(name, expected, tmp_path, capsys):
    if name.startswith("autorizacao."):
        case = name.split(".", 1)[1]
        request = json.loads((ROOT / "tests/fixtures/autorizacao-solicitacao.json").read_text())
        package = _package("000000")
        assert package is not None
        context = {"operadora": package}
        source = request
        if case == "aprovar-json":
            package["regras"][0]["check"]["codigos"] = ["99999999"]
        elif case == "pendente-json":
            request["solicitacao"].pop("indicacao_clinica")
        elif case in {"auditoria-xml", "sem-regra-xml"}:
            source = tiss.build_autorizacao(request)
            context = {} if case == "sem-regra-xml" else context
        elif case == "carteirinha-json":
            package["regras"][0]["check"]["codigos"] = ["99999999"]
            context["carteirinhas"] = {"AUT-0001": {"ativa": False}}
        result = tiss.check_autorizacao(source, contexto=context)
        assert result.decisao is not None
        assert result.decisao["tipo"] == expected
        assert expected in {"aprovar_por_regra", "pendente", "encaminhar_auditor"}
        assert (
            "negar"
            not in tiss.json_schema("report")["properties"]["decisao"]["properties"]["tipo"]["enum"]
        )
        assert "negar" not in result.to_json()
        if case == "aprovar-json":
            assert result.decisao["rules"]
            for example in ("autorizacao-solicitacao", "autorizacao-resposta"):
                xml = examples.load(example)
                assert tiss.build_autorizacao(tiss.parse_autorizacao(xml)) == xml
                assert tiss.validate(xml).valid
                hash_start = xml.index(b"<ans:hash>") + len(b"<ans:hash>")
                replacement = b"0" if xml[hash_start : hash_start + 1] != b"0" else b"1"
                changed = xml[:hash_start] + replacement + xml[hash_start + 1 :]
                assert "lote.hash_divergente" in {
                    finding.code for finding in tiss.validate(changed).findings
                }
        elif case == "pendente-json":
            assert result.decisao["needs"] == ["/solicitacao/indicacao_clinica"]
        elif case == "auditoria-xml":
            assert any(
                finding.code == "autorizacao.exige_auditoria"
                and finding.rule
                and finding.rule["id"] == "exige-autorizacao-consulta"
                for finding in result.findings
            )
        elif case == "sem-regra-xml":
            assert any(finding.code == "autorizacao.sem_regra" for finding in result.findings)
            assert result.decisao["rules"] == []
        elif case == "carteirinha-json":
            assert any(finding.code == "autorizacao.carteirinha" for finding in result.findings)
        return
    if name == "guia-consulta":
        lote = tiss.parse_lote(examples.load("lote-valido"))
        lote["numero_lote"] = "TISS-001"
        lote["guias"] = [
            {
                "tipo": "consulta",
                "cabecalho_consulta": {
                    "registro_ans": "123456",
                    "numero_guia_prestador": "CONSULTA-001",
                },
                "dados_beneficiario": {
                    "numero_carteira": "000000000001",
                    "atendimento_rn": "N",
                },
                "contratado_executante": {
                    "codigo_prestador_na_operadora": "PRESTADOR01",
                    "cnes": "1234567",
                },
                "profissional_executante": {
                    "nome_profissional": "DRA. MARIA COSTA",
                    "conselho_profissional": "01",
                    "numero_conselho_profissional": "12345",
                    "uf": "35",
                    "cbos": "225125",
                },
                "indicacao_acidente": "0",
                "dados_atendimento": {
                    "regime_atendimento": "01",
                    "data_atendimento": "2026-10-21",
                    "tipo_consulta": "1",
                    "procedimento": {
                        "codigo_tabela": "22",
                        "codigo_procedimento": "10101012",
                        "valor_procedimento": 15000,
                    },
                },
            }
        ]
        xml = tiss.build_lote(lote)
        assert tiss.validate(xml).valid
        parsed = tiss.parse_lote(xml)
        assert parsed == lote
        report = tiss.check(parsed)
        assert report.valid and report.findings == ()
        return
    if name.startswith("hash-"):
        root = etree.fromstring(examples.load("lote-valido"), parser())
        hash_element = root.xpath(".//ans:epilogo/ans:hash", namespaces=ANS)[0]
        if name == "hash-divergente":
            hash_element.text = "0" * 32
        else:
            hash_element.getparent().remove(hash_element)
        document = etree.tostring(root, encoding="ISO-8859-1", xml_declaration=True)
        report = tiss.validate(document)
        codes = {finding.code for finding in report.findings}
        if name == "hash-divergente":
            assert codes == {"lote.hash_divergente"}
            assert not report.valid
            finding = report.findings[0]
            assert finding.xpath.endswith("/ans:epilogo/ans:hash")
            assert finding.message == "Hash do epílogo divergente do calculado."
            assert finding.glosa == "5014"
            assert finding.fix is None
        else:
            assert "lote.hash_divergente" not in codes
            assert any(code.startswith("xsd.") for code in codes)
        return
    report = tiss.validate(examples.load(name))
    codes = {finding.code for finding in report.findings}
    assert expected <= codes
    if name == "lote-valido":
        assert report.valid and report.findings == ()
        empty_dir = tmp_path / "sem_lotes"
        empty_dir.mkdir()
        (empty_dir / "observacoes.txt").write_text("arquivo ignorado")
        assert cli_main(["validate", str(empty_dir)]) == 2
        assert capsys.readouterr().err == (
            f"Nenhum arquivo .xml ou .json encontrado em: {empty_dir.as_posix()}\n"
        )
    else:
        assert 1 <= sum(code.startswith("xsd.") for code in codes) <= 3
        assert report.findings[0].guia == "ERRO-01"
        assert {finding.guia for finding in report.findings if finding.guia} == {
            "ERRO-01",
            "ERRO-02",
        }
        assert any(finding.severity == "warning" for finding in report.findings)


def test_public_api_and_example_contract():
    _check_browser_map_contract()
    assert set(tiss.__all__) == {
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
        "rejection_map",
        "render_sadt",
        "sadt_catalog",
        "sadt_missing",
        "dominio",
        "operadoras",
        "validate",
        "validate_package",
    }
    assert set(tiss.json_schema("finding")["properties"]["code"]["enum"]) == set(CODES)
    assert tiss.examples.names() == [
        "lote-valido",
        "lote-com-erros",
        "demonstrativo",
        "autorizacao-solicitacao",
        "autorizacao-resposta",
    ]
    with pytest.raises(ValueError):
        tiss.examples.load("../unknown")
    request = json.loads((ROOT / "tests/fixtures/autorizacao-solicitacao.json").read_text())
    authorization_xml = tiss.build_autorizacao(request)
    with pytest.raises(tiss.AutorizacaoError):
        tiss.build_autorizacao({**request, "solicitacao": None, "autorizacao": {}})
    with pytest.raises(tiss.AutorizacaoError):
        tiss.build_autorizacao(
            {key: value for key, value in request.items() if key != "solicitacao"}
        )
    with pytest.raises(tiss.AutorizacaoError):
        tiss.build_autorizacao(
            {
                **request,
                "solicitacao": {**request["solicitacao"], "campo_desconhecido": "x"},
            }
        )
    with pytest.raises(tiss.AutorizacaoError):
        tiss.parse_autorizacao(
            authorization_xml.replace(b"SOLICITACAO_PROCEDIMENTOS", b"TIPO_INVALIDO")
        )


def _check_browser_map_contract():
    node = shutil.which("node")
    if (
        node is None
        or int(subprocess.check_output([node, "--version"]).decode()[1:].split(".")[0]) < 22
    ):
        return
    vectors = []
    for cpf, secret in [("000.000.000-00", "a" * 64), ("00000000001", "chave-sintética")]:
        lote = tiss.parse_lote(examples.load("lote-valido"))
        lote["prestador"] = {"cpf": cpf}
        value = tiss.rejection_map([lote], segredo_pseudonimo=secret)
        vectors.append([cpf, secret, value["providers"][0]["provider"]])
    script = r"""
import assert from "node:assert/strict";
import {
  identificarPrestador, lerCadastro, prepararCadastro, matrizDoMapa, rotuloDoPrestador,
} from "./web/lib/org/mapa.ts";
import { rotaPermitida } from "./web/lib/org/rotas.ts";
import { secoesVisiveisDaOrg } from "./web/components/org/secoes.ts";
for (const [cpf, secret, expected] of JSON.parse(process.argv[1])) {
  assert.equal(await identificarPrestador(cpf, async () => secret), expected);
}
const segredo = async () => "a".repeat(64);
const csv = 'provider,name\n000.000.000-00,"Clínica, Sintética"\n' +
  '00.000.000/0000-00,Hospital\ncodigo: A,Centro';
const itens = await prepararCadastro(lerCadastro(csv, false), segredo);
assert.match(itens[0].provider, /^cpf:hmac:[0-9a-f]{64}$/);
assert.equal(itens[0].name, "Clínica, Sintética");
assert.equal(itens[1].provider, "cnpj:00000000000000");
assert.equal(itens[2].provider, "codigo:A");
assert.deepEqual(lerCadastro("[]", true), []);
assert.deepEqual(await prepararCadastro([], segredo), []);
for (const body of [
  '[{"provider":"A","name":"X","extra":1}]', '[{"provider":"A","name":""}]', '{}',
]) {
  assert.throws(() => lerCadastro(body, true));
}
assert.throws(() => lerCadastro('provider,name\n"incompleto', false));
assert.throws(() => lerCadastro('name,provider\nA,X', false));
await assert.rejects(() => prepararCadastro([{provider:"cpf:abc",name:"X"}], segredo));
await assert.rejects(() => prepararCadastro(
  [{provider:"00000000000",name:"X"}], async () => {throw Error("indisponível")},
));
await assert.rejects(() => prepararCadastro(
  [{provider:"A",name:"X"},{provider:"codigo:A",name:"Y"}], segredo,
));
const prestador = {id:"codigo:A",name:null,name_source:null};
const linha = {
  provider:prestador, month:"2026-10", code:"X", glosa:null, rule_id:null,
  guias:2, affected_amount:"0.10",
};
const matriz = matrizDoMapa([linha,{...linha,affected_amount:"0.20"},{...linha,month:null}]);
assert.deepEqual(matriz.meses, ["2026-10","sem mês"]);
assert.deepEqual(matriz.linhas[0].total, {guias:6,centavos:40});
assert.deepEqual(matrizDoMapa([]), {meses:[],linhas:[]});
assert.equal(rotuloDoPrestador(prestador), "Código A");
assert.equal(rotuloDoPrestador({...prestador,id:"cnpj:00000000000000"}), "00.000.000/0000-00");
assert.equal(
  rotuloDoPrestador({...prestador,id:"cpf:hmac:"+"a".repeat(64)}), "CPF pseudonimizado …aaaa",
);
const org = {
  type:"pay",is_admin:false,my_areas:["auditoria"],rejection_map:{eligible:true,enabled:false},
};
const visivel = (value) => secoesVisiveisDaOrg(value).some(s => s.key === "mapa");
assert.equal(visivel(org), true);
assert.equal(visivel({...org,my_areas:[]}), false);
assert.equal(visivel({...org,type:"prov"}), false);
assert.equal(visivel({...org,rejection_map:{eligible:false}}), false);
assert.equal(visivel({...org,my_areas:["administration"]}), true);
const base = "org/org-1/tiss/rejection-map/";
for (const [path, methods] of [
  [base,["GET","DELETE"]], [base+"enable/",["POST"]], [base+"disable/",["POST"]],
  [base+"secret/",["GET"]], [base+"provider/",["PUT"]],
]) {
  for (const method of ["GET","POST","PUT","DELETE","PATCH"]) {
    assert.equal(rotaPermitida(path, method), methods.includes(method));
  }
}
assert.equal(rotaPermitida(base+"extra/", "GET"), false);
"""
    subprocess.run(
        [
            node,
            "--experimental-strip-types",
            "--input-type=module",
            "-e",
            script,
            json.dumps(vectors),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_generated_artifacts_and_golden_report_are_current():
    assert manutencao._write_artifacts(check=True)
    expected = (ROOT / "tests/golden/lote-com-erros.report.json").read_text().strip()
    assert tiss.validate(tiss.examples.load("lote-com-erros")).to_json() == expected


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
        tiss.validate(examples.load("lote-valido")),
        tiss.validate(examples.load("lote-com-erros")),
        tiss.validate((ROOT / "tests/fixtures/xml/malformed.xml").read_bytes()),
    ]
    validator = jsonschema.Draft202012Validator(tiss.json_schema("report"))
    for report in reports:
        validator.validate(report.to_dict())
        assert json.loads(report.to_json()) == report.to_dict()
    code = (
        "from tiss import examples,validate;"
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
    assert tiss.validate(examples.load("lote-valido")).valid
    assert tiss.parse_demonstrativo(examples.load("demonstrativo"))
    from tiss.tuss import lookup, search

    assert lookup("10101012", tabela="22")
    assert search("consultorio")
    assert tiss.sadt_catalog()
    assert isinstance(tiss.sadt_missing({}), list)


def test_sadt_catalog_completeness_and_optional_dependencies(monkeypatch, tmp_path):
    original_import = builtins.__import__

    def without_pdf(name, *args, **kwargs):
        if name.split(".", 1)[0] in {"weasyprint", "jinja2", "markupsafe"}:
            raise ImportError(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_pdf)
    assert sadt_catalog()["fields"]
    assert isinstance(sadt_missing({}), list)
    with pytest.raises(MissingExtraError, match="tiss\\[pdf\\]"):
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

    from tiss._line_total import LineTotalError, line_total, line_total_cents

    assert line_total(unit_price="12.50", quantity=2) == Decimal("25.00")
    assert line_total_cents(unit_price_cents=7, quantity=3, factor="0.5") == Decimal("10.5")
    with pytest.raises(LineTotalError):
        line_total(unit_price="12.50", quantity=0)
    html = render_html({"beneficiario_nome": "<script>injection</script>"}, load_bundle())
    assert "&lt;script&gt;" in html and "<script>injection</script>" not in html


def _png() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        checksum = struct.pack(">I", zlib.crc32(kind + data))
        return struct.pack(">I", len(data)) + kind + data + checksum

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pixels = zlib.compress(b"\x00\xff\x00\x00")
    return (
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")
    )


def test_sadt_pdf_embeds_only_explicit_logo(tmp_path, monkeypatch):
    pytest.importorskip("weasyprint")

    class Recorder(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.server.requests.append(self.path)
            self.send_response(404)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Recorder)
    server.requests = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    png_path = tmp_path / "logo.png"
    png_path.write_bytes(_png())
    bundle = load_bundle()
    hostile = dataclasses.replace(
        bundle,
        template_html=bundle.template_html.replace(
            "<body>",
            f'<body><img src="{base}/img"><img src="{png_path.as_uri()}">'
            f'<link rel="stylesheet" href="{base}/css">',
            1,
        ),
        template_css=bundle.template_css + f'body {{ background: url("{base}/fundo") }}',
    )

    def images(path):
        return sum(len(page.images) for page in PdfReader(path).pages)

    try:
        with monkeypatch.context() as patch:
            patch.setattr("tiss._sadt.load_bundle", lambda: hostile)
            output = tmp_path / "hostil.pdf"
            render_sadt({"logo_src": f"{base}/logo"}, output, gen_date=datetime.date(2026, 6, 22))
            assert images(output) == 0
        for logo in (png_path, _png()):
            output = tmp_path / "logo.pdf"
            render_sadt({}, output, logo=logo)
            assert images(output) == 1
    finally:
        server.shutdown()
    assert server.requests == []
    html = render_html({"logo_src": png_path.as_uri()}, bundle, logo=b"\xff\xd8\xff\xe0")
    assert "data:image/jpeg;base64," in html and png_path.as_uri() not in html
    with pytest.raises(ValueError, match="PNG ou JPEG"):
        render_html({}, bundle, logo=b"GIF89a")


@pytest.mark.parametrize("task", gerar(), ids=lambda task: task["id"])
def test_benchmark_task_contract(task):
    path = TASK_DIR / f"{task['id']}.json"
    assert json.loads(path.read_text(encoding="utf-8")) == task
    assert verificar(task, task["referencia"])[0]
    assert not verificar(task, task["errada"])[0]
