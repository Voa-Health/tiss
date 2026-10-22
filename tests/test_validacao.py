from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import jsonschema
import pytest
from conftest import ANS, ROOT, mutate, remove_element, set_text
from lxml import etree

import voa_tiss
from voa_tiss import examples
from voa_tiss._rules import _package, validate_package
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
        ("autorizacao.aprovar-json", "aprovar_por_regra"),
        ("autorizacao.pendente-json", "pendente"),
        ("autorizacao.auditoria-xml", "encaminhar_auditor"),
        ("autorizacao.sem-regra-xml", "encaminhar_auditor"),
        ("autorizacao.carteirinha-json", "encaminhar_auditor"),
    ],
)
def test_example_reports(name, expected):
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
        elif case == "auditoria-xml":
            source = voa_tiss.build_autorizacao(request)
        elif case == "sem-regra-xml":
            source = voa_tiss.build_autorizacao(request)
            context = {}
        elif case == "carteirinha-json":
            package["regras"][0]["check"]["codigos"] = ["99999999"]
            context["carteirinhas"] = {"AUT-0001": {"ativa": False}}
        result = voa_tiss.check_autorizacao(source, contexto=context)
        assert result.decisao is not None
        assert result.decisao["tipo"] == expected
        assert expected in {"aprovar_por_regra", "pendente", "encaminhar_auditor"}
        assert (
            "negar"
            not in voa_tiss.json_schema("report")["properties"]["decisao"]["properties"]["tipo"][
                "enum"
            ]
        )
        assert "negar" not in result.to_json()
        if case == "aprovar-json":
            assert result.decisao["rules"]
            for example in ("autorizacao-solicitacao", "autorizacao-resposta"):
                xml = examples.load(example)
                assert voa_tiss.build_autorizacao(voa_tiss.parse_autorizacao(xml)) == xml
                assert voa_tiss.validate(xml).valid
                hash_start = xml.index(b"<ans:hash>") + len(b"<ans:hash>")
                replacement = b"0" if xml[hash_start : hash_start + 1] != b"0" else b"1"
                assert "lote.hash_divergente" in {
                    finding.code
                    for finding in voa_tiss.validate(
                        xml[:hash_start] + replacement + xml[hash_start + 1 :]
                    ).findings
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
        ("exige_autorizacao.valido", False),
        ("exige_autorizacao.invalido", True),
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
    if case == "exige_autorizacao.invalido":
        assert findings[0].glosa == "1818"
        audit_findings = [
            finding for finding in voa_tiss.audit(lote, operadora=package).findings if finding.rule
        ]
        assert audit_findings[0].rule["id"] == case
        assert audit_findings[0].glosa == "1818"


def test_hash_uses_iso_8859_1_and_ignores_comments():
    prefix = b'<?xml version="1.0" encoding="ISO-8859-1"?><root xmlns:ans="'
    namespace = b"http://www.ans.gov.br/padroes/tiss/schemas"
    suffix = b'"><value>Jo\xe3o</value><ans:hash>old</ans:hash></root>'
    without_comment = prefix + namespace + suffix
    comment = b'"><value>Jo\xe3o</value><!-- not a value --><ans:hash>old</ans:hash></root>'
    expected = hashlib.md5("João".encode("iso-8859-1")).hexdigest()
    assert voa_tiss.hash_epilogo(without_comment) == expected
    assert voa_tiss.hash_epilogo(prefix + namespace + comment) == expected
