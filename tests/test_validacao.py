from __future__ import annotations

import hashlib
import io
import json
from copy import deepcopy
from datetime import date
from urllib import request

import jsonschema
import pytest
from conftest import ANS, ROOT, mutate, remove_element, set_text
from lxml import etree

import voa_tiss
from voa_tiss import examples
from voa_tiss.__main__ import main as cli_main
from voa_tiss._mapa_html import render_rejection_map_html
from voa_tiss._rules import validate_package
from voa_tiss._schema import parser
from voa_tiss.codes import CODES


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
    ],
)
def test_example_reports(name, expected):
    if name == "guia-consulta":
        lote = voa_tiss.parse_lote(examples.load("lote-valido"))
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
        xml = voa_tiss.build_lote(lote)
        assert voa_tiss.validate(xml).valid
        parsed = voa_tiss.parse_lote(xml)
        assert parsed == lote
        report = voa_tiss.check(parsed)
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
        report = voa_tiss.validate(document)
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
    report = voa_tiss.validate(examples.load(name))
    codes = {finding.code for finding in report.findings}
    assert expected <= codes
    if name == "lote-valido":
        assert report.valid and report.findings == ()
    else:
        assert 1 <= sum(code.startswith("xsd.") for code in codes) <= 3
        assert report.findings[0].guia == "ERRO-01"
        assert {finding.guia for finding in report.findings if finding.guia} == {
            "ERRO-01",
            "ERRO-02",
        }
        assert any(finding.severity == "warning" for finding in report.findings)


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        (b'<?xml version="1.0" encoding="UTF-8"?><r>\xff</r>', "xml.encoding"),
        ("<r>\x01</r>", "xml.encoding"),
        ("<r>", "xml.malformado"),
        (examples.load("lote-valido").replace(b"4.03.00", b"4.01.00"), "versao.nao_suportada"),
        (b"<root/>", "versao.nao_detectada"),
    ],
)
def test_parse_errors_and_versions(document, expected):
    assert expected in {finding.code for finding in voa_tiss.validate(document).findings}


def test_doctype_encoding_version_and_input_contract():
    malformed = voa_tiss.validate("<root>")
    assert "linha" in malformed.findings[0].message
    doctype = (ROOT / "tests/fixtures/xml/doctype.xml").read_bytes()
    assert [finding.code for finding in voa_tiss.validate(doctype).findings] == ["xml.doctype"]
    latin = '<?xml version="1.0" encoding="ISO-8859-1"?><root>João</root>'.encode("latin-1")
    for document in (latin, latin.decode("latin-1")):
        assert "xml.encoding" not in {
            finding.code for finding in voa_tiss.validate(document).findings
        }
    report = voa_tiss.validate(examples.load("lote-valido"))
    assert report.version == "4.03.00" and report.valid
    divergent = voa_tiss.validate(examples.load("lote-valido"), version="4.01.00")
    assert {"versao.divergente", "versao.nao_suportada"} <= {
        finding.code for finding in divergent.findings
    }
    fixtures = ROOT / "tests/fixtures/xml"
    valid_402 = voa_tiss.validate((fixtures / "4.02.00-valido.xml").read_bytes())
    invalid_402 = voa_tiss.validate((fixtures / "4.02.00-invalido.xml").read_bytes())
    assert valid_402.version == "4.02.00" and valid_402.valid
    assert any(finding.code.startswith("xsd.") for finding in invalid_402.findings)
    with pytest.raises(TypeError):
        voa_tiss.validate(42)  # type: ignore[arg-type]
    prefix = b'<?xml version="1.0" encoding="ISO-8859-1"?><root xmlns:ans="'
    namespace = b"http://www.ans.gov.br/padroes/tiss/schemas"
    suffix = b'"><value>Jo\xe3o</value><ans:hash>old</ans:hash></root>'
    without_comment = prefix + namespace + suffix
    comment = b'"><value>Jo\xe3o</value><!-- not a value --><ans:hash>old</ans:hash></root>'
    expected = hashlib.md5("João".encode("iso-8859-1")).hexdigest()
    assert voa_tiss.hash_epilogo(without_comment) == expected
    assert voa_tiss.hash_epilogo(prefix + namespace + comment) == expected


@pytest.mark.parametrize(
    ("code", "expected_fragments", "requires_needs"),
    [
        ("xsd.atributo", (), False),
        ("xsd.elemento_inesperado", ("inesperado em cabecalho; esperado:",), True),
        ("xsd.elemento_ausente", ("Falta elemento em",), True),
        ("xsd.padrao", ("CNPJ", "0000000000000X"), False),
        ("xsd.enumeracao", ("caraterAtendimento", "X"), False),
        ("xsd.tamanho", ("numeroCarteira", "21"), False),
        ("xsd.tipo", ("dataExecucao", "2026-99-99"), False),
        ("xsd.outro", (), False),
    ],
)
def test_xsd_messages_are_specific(code, expected_fragments, requires_needs, xsd_cases):
    finding = next(
        item for item in voa_tiss.validate(xsd_cases[code]).findings if item.code == code
    )
    assert "{" not in finding.message
    assert all(fragment in finding.message for fragment in expected_fragments)
    assert bool(finding.needs) is requires_needs


def test_rule_catalog_covers_fixtures_and_reports_validate(xsd_cases):
    documents = {
        path.name: path.read_bytes() for path in (ROOT / "tests/fixtures/xml").glob("*.xml")
    }
    documents.update({name: examples.load(name) for name in examples.names()})
    documents.update(xsd_cases)
    documents["encoding"] = b'<?xml version="1.0" encoding="utf-8"?><x>\xff</x>'

    def duplicate_guide_number(root):
        guides = root.xpath(".//ans:guiaSP-SADT", namespaces=ANS)
        first, second = guides
        number = first.findtext("ans:cabecalhoGuia/ans:numeroGuiaPrestador", namespaces=ANS)
        set_text(second, "ans:cabecalhoGuia/ans:numeroGuiaPrestador", number)

    documents["duplicate"] = mutate(duplicate_guide_number)
    documents["missing-card"] = mutate(lambda root: remove_element(root, ".//ans:numeroCarteira"))
    all_codes: set[str] = set()
    validator = jsonschema.Draft202012Validator(voa_tiss.json_schema("report"))
    for document in documents.values():
        report = voa_tiss.validate(document)
        all_codes.update(finding.code for finding in report.findings)
        validator.validate(report.to_dict())
    all_codes.update(
        finding.code
        for finding in voa_tiss.validate(examples.load("lote-valido"), version="4.02.00").findings
    )
    assert all_codes <= CODES.keys()


def test_xpaths_resolve_with_prefixed_and_default_namespaces():
    prefixed = examples.load("lote-com-erros")
    default = prefixed.replace(b"xmlns:ans=", b"xmlns=").replace(b"ans:", b"")
    reports = [voa_tiss.validate(document) for document in (prefixed, default)]
    sets = []
    for document, report in zip((prefixed, default), reports, strict=True):
        tree = etree.fromstring(document, parser())
        for finding in report.findings:
            if finding.xpath:
                assert len(tree.xpath(finding.xpath, namespaces=ANS)) == 1
        sets.append({(finding.code, finding.guia) for finding in report.findings})
    assert sets[0] == sets[1]


@pytest.mark.parametrize(
    ("case", "fails"),
    [
        ("obrigatorio.valido", False),
        ("obrigatorio.invalido", True),
        ("padrao.valido", False),
        ("padrao.invalido", True),
        ("valores.valido", False),
        ("valores.invalido", True),
        ("max_itens.valido", False),
        ("max_itens.invalido", True),
        ("combinacao_proibida.valido", False),
        ("combinacao_proibida.invalido", True),
        ("official.comunidade.false", False),
        ("official.operadora.true", False),
        ("official.comunidade.true", True),
        ("official.operadora.false", True),
    ],
)
def test_operator_rule_cases(valid_lote, operator_rules, case, fails):
    package = deepcopy(operator_rules)
    assert not validate_package(package)
    if case.startswith("official."):
        _, maintainer, official = case.split(".")
        package["mantenedor"]["tipo"] = maintainer
        package["official"] = official == "true"
        package["regras"] = []
        assert bool(validate_package(package)) is fails
        return
    package["regras"] = [rule for rule in package["regras"] if rule["id"] == case]
    assert not validate_package(package)
    lote = deepcopy(valid_lote)
    if case == "combinacao_proibida.invalido":
        lote["operadora"]["registro_ans"] = "419761"
    findings = [
        finding for finding in voa_tiss.check(lote, operadora=package).findings if finding.rule
    ]
    assert bool(findings) is fails


def test_mapa_de_rejeicao(tmp_path, monkeypatch, capsys):
    base = voa_tiss.parse_lote(examples.load("lote-valido"))
    base["transacao"]["data_registro_transacao"] = "2026-10-21"
    for guide in base["guias"]:
        guide["procedimentos_executados"][0]["data_execucao"] = "2026-10-21"

    rules = json.loads((ROOT / "tests/fixtures/rules/000000.json").read_text())
    rules["operadora"] = "123456"
    rule = next(item for item in rules["regras"] if item["id"] == "padrao.invalido")
    rule["check"]["pointer"] = "/guias/*/cabecalho_guia/numero_guia_prestador"
    rule["check"]["regex"] = "^GUIA-1$"
    rules["regras"] = [rule]
    code_lote = deepcopy(base)
    code_lote["prestador"] = {"codigo_prestador_na_operadora": "CLINICA-A"}
    code_lote["guias"][0]["cabecalho_guia"]["numero_guia_prestador"] = "GUIA-1"
    code_lote["guias"][1]["cabecalho_guia"]["numero_guia_prestador"] = "GUIA-2"
    rule_findings = voa_tiss.check(code_lote, operadora=rules).findings
    rule_finding = next(finding for finding in rule_findings if finding.rule)

    cnpj_lote = deepcopy(base)
    cnpj_lote["prestador"] = {"cnpj": "11222333000181"}
    xml_root = etree.fromstring(voa_tiss.build_lote(cnpj_lote), parser())
    hash_element = xml_root.xpath(".//ans:epilogo/ans:hash", namespaces=ANS)[0]
    hash_element.text = "0" * 32
    hash_xml = etree.tostring(xml_root, encoding="ISO-8859-1", xml_declaration=True)
    hash_finding = next(
        finding
        for finding in voa_tiss.validate(hash_xml, operadora=rules).findings
        if finding.code == "lote.hash_divergente"
    )
    assert hash_finding.glosa is not None

    cpf = "12345678909"
    secret = "s" * 16
    cpf_lote = deepcopy(base)
    cpf_lote["prestador"] = {"cpf": "123.456.789-09"}
    result = voa_tiss.rejection_map(
        [code_lote, hash_xml, cpf_lote],
        operadora=rules,
        segredo_pseudonimo=secret,
        at=date(2026, 10, 21),
    )
    provider_rows = {item["prestador"]: item for item in result["prestadores"]}
    cpf_id = next(provider for provider in provider_rows if provider.startswith("cpf:hmac:"))
    assert result["lotes"] == 3
    assert result["guias"] == 6
    assert result["ignorados"] == []
    assert provider_rows["codigo:CLINICA-A"]["guias"] == 2
    assert provider_rows["codigo:CLINICA-A"]["guias_com_achado"] == 1
    assert provider_rows["codigo:CLINICA-A"]["valor_afetado"] == "100.00"
    assert provider_rows["cnpj:11222333000181"]["guias_com_achado"] == 2
    assert provider_rows["cnpj:11222333000181"]["valor_afetado"] == "200.00"
    assert provider_rows[cpf_id]["guias_com_achado"] == 2
    assert provider_rows[cpf_id]["valor_afetado"] == "200.00"
    assert provider_rows[cpf_id]["mes"] == "2026-10"

    rule_line = next(
        item
        for item in result["linhas"]
        if item["prestador"] == "codigo:CLINICA-A" and item["rule_id"] == rule_finding.rule["id"]
    )
    assert rule_line["codigo"] == rule_finding.code
    assert rule_line["guias"] == 1
    hash_line = next(item for item in result["linhas"] if item["codigo"] == hash_finding.code)
    assert hash_line["glosa"] == hash_finding.glosa
    assert hash_line["guias"] == 2
    assert hash_line["valor_afetado"] == "200.00"

    cpf_unformatted = deepcopy(cpf_lote)
    cpf_unformatted["prestador"]["cpf"] = cpf
    equivalent = voa_tiss.rejection_map([cpf_unformatted], segredo_pseudonimo=secret)
    changed_secret = voa_tiss.rejection_map([cpf_unformatted], segredo_pseudonimo="t" * 16)
    assert equivalent["prestadores"][0]["prestador"] == cpf_id
    assert changed_secret["prestadores"][0]["prestador"] != cpf_id
    with pytest.raises(ValueError, match="Informe segredo_pseudonimo"):
        voa_tiss.rejection_map([cpf_unformatted])

    encoded = json.dumps(result, ensure_ascii=False)
    html = render_rejection_map_html(result)
    assert cpf not in encoded and cpf not in html
    assert "hmac:" in encoded
    assert "<script" not in html.lower()
    assert 'href="http' not in html.lower() and 'src="http' not in html.lower()
    jsonschema.Draft202012Validator(voa_tiss.json_schema("rejection_map")).validate(result)

    folder = tmp_path / "lotes"
    folder.mkdir()
    (folder / "a.json").write_text(json.dumps(code_lote), encoding="utf-8")
    (folder / "b.xml").write_bytes(hash_xml)
    (folder / "c.json").write_text(json.dumps(cpf_lote), encoding="utf-8")
    monkeypatch.setenv("VOA_TISS_SEGREDO_PSEUDONIMO", secret)
    assert cli_main(["mapa", str(folder)]) == 0
    stdout = capsys.readouterr()
    cli_result = json.loads(stdout.out)
    assert cpf not in stdout.out
    assert cpf not in json.dumps(cli_result)

    json_path = tmp_path / "mapa.json"
    html_path = tmp_path / "mapa.html"
    assert cli_main(["mapa", str(folder), "--json", str(json_path), "--html", str(html_path)]) == 0
    capsys.readouterr()
    assert cpf not in json_path.read_text(encoding="utf-8")
    saved_html = html_path.read_text(encoding="utf-8")
    assert cpf not in saved_html
    assert "<script" not in saved_html.lower()

    monkeypatch.delenv("VOA_TISS_MAPA_URL", raising=False)
    monkeypatch.delenv("VOA_TISS_KEY", raising=False)
    assert cli_main(["mapa", str(folder), "--enviar"]) == 2
    assert "Defina VOA_TISS_MAPA_URL e VOA_TISS_KEY" in capsys.readouterr().err
    sent: dict[str, object] = {}

    def urlopen(req, timeout):
        sent["request"] = req
        sent["timeout"] = timeout
        return io.BytesIO()

    monkeypatch.setattr(request, "urlopen", urlopen)
    monkeypatch.setenv("VOA_TISS_MAPA_URL", "https://mapa.example.invalid/")
    monkeypatch.setenv("VOA_TISS_KEY", "k" * 16)
    assert cli_main(["mapa", str(folder), "--json", str(json_path), "--enviar"]) == 0
    request_sent = sent["request"]
    assert request_sent.data == json_path.read_bytes().rstrip(b"\n")
    assert request_sent.get_header("Authorization") == f"Bearer {'k' * 16}"
    assert request_sent.get_header("Content-type") == "application/json"
    assert sent["timeout"] == 10
