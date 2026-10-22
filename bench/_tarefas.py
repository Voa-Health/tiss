from __future__ import annotations

import copy
import datetime
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from lxml import etree

import voa_tiss
from voa_tiss import audit, dominio, examples, glosa, parse_demonstrativo, parse_lote, sandbox
from voa_tiss.tuss import lookup

ROOT = Path(__file__).resolve().parent
TASK_DIR = ROOT / "tarefas"
_DATE = "2026-10-21"
_PROCEDURES = ("10101012", "10101039")
_NAMES = ("JOSÉ DA SILVA", "CLÍNICA SÃO JOÃO", "ANA LÚCIA MENDES")
_TABLE38_CODES = ("1017", "1801", "1802")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)


def _bytes(xml: bytes | str) -> bytes:
    return xml.encode("ISO-8859-1") if isinstance(xml, str) else xml


def _xml_text(xml: bytes | str) -> str:
    if isinstance(xml, str):
        return xml
    root = etree.fromstring(xml)
    return etree.tostring(
        root,
        encoding="ISO-8859-1",
        xml_declaration=True,
    ).decode("ISO-8859-1")


def _parse_xml(xml: bytes | str) -> etree._Element:
    return etree.fromstring(_bytes(xml))


def _write_hash(root: etree._Element) -> bytes:
    hash_node = root.xpath("//*[local-name()='epilogo']/*[local-name()='hash']")[0]
    hash_node.text = voa_tiss.hash_epilogo(etree.tostring(root))
    return etree.tostring(root, xml_declaration=True, encoding="ISO-8859-1")


def _procedure(code: str) -> dict[str, str]:
    records = lookup(code, include_expired=True, today=datetime.date.fromisoformat(_DATE))
    if not records:
        raise ValueError(f"Código TUSS ausente: {code}")
    row = records[0]
    return {
        "codigo_tabela": str(row["tabela"]),
        "codigo_procedimento": str(row["codigo"]),
        "descricao_procedimento": str(row["termo"]),
    }


def _format_money(cents: int) -> str:
    return f"R$ {cents // 100},{cents % 100:02d}"


def _new_lote(guide_count: int, item_counts: list[int] | None = None) -> dict[str, Any]:
    lote = parse_lote(examples.load("lote-valido"))
    lote["numero_lote"] = "TISS-001"
    lote["transacao"].update(
        {
            "data_registro_transacao": _DATE,
            "hora_registro_transacao": "12:00:00",
            "sequencial_transacao": "1792673811",
        }
    )
    lote["guias"] = []
    item_counts = item_counts or [1] * guide_count
    for guide_index in range(guide_count):
        guide = copy.deepcopy(parse_lote(examples.load("lote-valido"))["guias"][0])
        guide["cabecalho_guia"] = {
            "registro_ans": "123456",
            "numero_guia_prestador": f"G-{guide_index + 1:04d}",
        }
        guide["dados_beneficiario"] = {
            "numero_carteira": f"00000000000{guide_index + 1}",
            "atendimento_rn": "N",
        }
        guide["dados_solicitante"]["nome_contratado_solicitante"] = "CLÍNICA SÃO JOÃO"
        guide["dados_solicitante"]["profissional_solicitante"].update(
            {
                "nome_profissional": "DRA. MARIA COSTA",
                "conselho_profissional": "01",
                "numero_conselho_profissional": "12345",
                "uf": "35",
                "cbos": "225125",
            }
        )
        guide["dados_executante"]["contratado_executante"]["codigo_prestador_na_operadora"] = (
            "PRESTADOR01"
        )
        guide["dados_executante"]["cnes"] = "1234567"
        items = []
        for item_index in range(item_counts[guide_index]):
            code = _PROCEDURES[item_index % len(_PROCEDURES)]
            unit = 12500 + guide_index * 500 + item_index * 250
            quantity = "2" if item_index == 1 else "1"
            total = unit * int(quantity)
            items.append(
                {
                    "sequencial_item": str(item_index + 1),
                    "data_execucao": _DATE,
                    "procedimento": _procedure(code),
                    "quantidade_executada": quantity,
                    "reducao_acrescimo": "1.00",
                    "valor_unitario": unit,
                    "valor_total": total,
                }
            )
        guide["procedimentos_executados"] = items
        subtotal = sum(item["valor_total"] for item in items)
        guide["valor_total"] = {
            "valor_procedimentos": subtotal,
            "valor_total_geral": subtotal,
        }
        guide["dados_atendimento"].update(
            {
                "indicacao_acidente": "0",
                "regime_atendimento": "01",
                "tipo_atendimento": "01",
            }
        )
        lote["guias"].append(guide)
    return lote


def _xml_lote(lote: dict[str, Any]) -> bytes:
    return voa_tiss.build_lote(lote)


def _xml_consulta(lote: dict[str, Any]) -> bytes:
    for guide in lote["guias"]:
        guide["tipo"] = "consulta"
        guide["cabecalho_consulta"] = {
            "registro_ans": "123456",
            "numero_guia_prestador": guide["cabecalho_guia"]["numero_guia_prestador"],
        }
        guide.pop("cabecalho_guia")
        guide.pop("dados_solicitante")
        guide.pop("dados_solicitacao")
        guide.pop("dados_executante")
        guide.pop("procedimentos_executados")
        guide.pop("valor_total")
        guide["contratado_executante"] = {
            "codigo_prestador_na_operadora": "PRESTADOR01",
            "cnes": "1234567",
        }
        guide["profissional_executante"] = {
            "nome_profissional": "DRA. MARIA COSTA",
            "conselho_profissional": "01",
            "numero_conselho_profissional": "12345",
            "uf": "35",
            "cbos": "225125",
        }
        guide["indicacao_acidente"] = "0"
        guide["dados_atendimento"] = {
            "regime_atendimento": "01",
            "data_atendimento": _DATE,
            "tipo_consulta": "1",
            "procedimento": {
                "codigo_tabela": "22",
                "codigo_procedimento": "10101012",
                "valor_procedimento": 15000,
            },
        }
    return _xml_lote(lote)


def _case_text(lote: dict[str, Any]) -> str:
    lines = [
        f"Transação: {_DATE} às 12:00:00; prestador CNPJ 00000000000000; operadora ANS 123456.",
        f"Número do lote: {lote['numero_lote']}.",
    ]
    for index, guide in enumerate(lote["guias"], start=1):
        header_key = "cabecalho_consulta" if guide["tipo"] == "consulta" else "cabecalho_guia"
        header = guide[header_key]
        data = guide.get("dados_atendimento", {})
        accident = guide.get("indicacao_acidente", data.get("indicacao_acidente", "0"))
        lines.extend(
            [
                f"Guia {index}: tipo {guide['tipo']}; número "
                f"{header['numero_guia_prestador']}; beneficiário "
                f"{_NAMES[(index - 1) % len(_NAMES)]}; carteira "
                f"{guide['dados_beneficiario']['numero_carteira']}; atendimento RN N.",
                "Contratado: PRESTADOR01, CLÍNICA SÃO JOÃO, CNES 1234567.",
                "Profissional: DRA. MARIA COSTA, conselho 01, número 12345, UF 35, CBOS 225125.",
                f"Indicação de acidente {accident}; "
                f"regime de atendimento {data.get('regime_atendimento', '01')}; data {_DATE}.",
            ]
        )
        if guide["tipo"] == "consulta":
            procedure = data["procedimento"]
            description = _procedure(procedure["codigo_procedimento"])["descricao_procedimento"]
            lines.append(
                f"Tipo de consulta {data['tipo_consulta']}; procedimento tabela "
                f"{procedure['codigo_tabela']}, código {procedure['codigo_procedimento']}, "
                f"descrição {description}, "
                f"quantidade 1, valor unitário {_format_money(procedure['valor_procedimento'])}."
            )
        else:
            lines.append(
                f"Caráter de atendimento {guide['dados_solicitacao']['carater_atendimento']}; "
                f"tipo de atendimento {data['tipo_atendimento']}."
            )
            for item in guide["procedimentos_executados"]:
                proc = item["procedimento"]
                lines.append(
                    f"Procedimento tabela {proc['codigo_tabela']}, "
                    f"código {proc['codigo_procedimento']}, descrição "
                    f"{proc['descricao_procedimento']}, quantidade "
                    f"{item['quantidade_executada']}, valor unitário "
                    f"{_format_money(item['valor_unitario'])}."
                )
    return "\n".join(lines)


def _expected_lote(xml: bytes | str) -> dict[str, Any]:
    lote = parse_lote(xml)
    fields: dict[str, Any] = {
        "/operadora/registro_ans": lote["operadora"]["registro_ans"],
        "/numero_lote": lote["numero_lote"],
    }
    for guide_index, guide in enumerate(lote["guias"]):
        header = "cabecalho_consulta" if guide["tipo"] == "consulta" else "cabecalho_guia"
        fields[f"/guias/{guide_index}/{header}/numero_guia_prestador"] = guide[header][
            "numero_guia_prestador"
        ]
        fields[f"/guias/{guide_index}/dados_beneficiario/numero_carteira"] = guide[
            "dados_beneficiario"
        ]["numero_carteira"]
        if guide["tipo"] == "consulta":
            data = guide["dados_atendimento"]
            procedure = data["procedimento"]
            base = f"/guias/{guide_index}/dados_atendimento"
            for field in ("codigo_tabela", "codigo_procedimento", "valor_procedimento"):
                fields[f"{base}/procedimento/{field}"] = procedure[field]
            fields[f"{base}/tipo_consulta"] = data["tipo_consulta"]
        else:
            for item_index, item in enumerate(guide["procedimentos_executados"]):
                base = f"/guias/{guide_index}/procedimentos_executados/{item_index}"
                for field in (
                    "codigo_tabela",
                    "codigo_procedimento",
                ):
                    fields[f"{base}/procedimento/{field}"] = item["procedimento"][field]
                for field in ("quantidade_executada", "valor_unitario", "valor_total"):
                    fields[f"{base}/{field}"] = item[field]
            fields[f"/guias/{guide_index}/valor_total/valor_total_geral"] = guide["valor_total"][
                "valor_total_geral"
            ]
    return {"guias": len(lote["guias"]), "campos": fields}


def _task(
    task_id: str,
    category: str,
    perspective: str,
    instruction: str,
    output_format: str,
    expected: dict[str, Any],
    reference: str,
    wrong: str,
) -> dict[str, Any]:
    return {
        "id": task_id,
        "categoria": category,
        "perspectiva": perspective,
        "instrucao": instruction,
        "formato": output_format,
        "esperado": expected,
        "referencia": reference,
        "errada": wrong,
    }


def _generation_tasks() -> list[dict[str, Any]]:
    tasks = []
    for index in range(1, 5):
        perspective = "profissional" if index < 3 else "prestador"
        count = 2 if index == 2 else 1
        lote = _new_lote(count)
        xml = _xml_consulta(lote)
        task_id = f"gerar-consulta-{index:02d}"
        instruction = (
            "Monte um lote TISS 4.03.00 (prestadorParaOperadora, envio de lote de guias) "
            "para o caso abaixo e devolva o XML completo, com o hash do epílogo correto.\n\n"
            f"Caso:\n{_case_text(lote)}\n\nResposta: apenas o XML."
        )
        wrong_xml = _parse_xml(xml)
        wrong_xml.xpath("//*[local-name()='valorProcedimento']")[0].text = "1.00"
        tasks.append(
            _task(
                task_id,
                "gerar",
                perspective,
                instruction,
                "xml",
                _expected_lote(xml),
                _xml_text(xml),
                _xml_text(etree.tostring(wrong_xml)),
            )
        )
    for index in range(1, 5):
        counts = [1, 1]
        if index == 2:
            counts = [1, 1]
        elif index == 4:
            counts = [3]
        lote = _new_lote(len(counts), counts)
        xml = _xml_lote(lote)
        task_id = f"gerar-sp-sadt-{index:02d}"
        instruction = (
            "Monte um lote TISS 4.03.00 (prestadorParaOperadora, envio de lote de guias) "
            "para o caso abaixo e devolva o XML completo, com o hash do epílogo correto.\n\n"
            f"Caso:\n{_case_text(lote)}\n\nResposta: apenas o XML."
        )
        wrong_xml = _parse_xml(xml)
        wrong_xml.xpath("//*[local-name()='valorTotalGeral']")[0].text = "1.00"
        tasks.append(
            _task(
                task_id,
                "gerar",
                "prestador",
                instruction,
                "xml",
                _expected_lote(xml),
                _xml_text(xml),
                _xml_text(etree.tostring(wrong_xml)),
            )
        )
    return tasks


def _mutated_lote(xml: bytes, mutation: int) -> tuple[str, str]:
    root = _parse_xml(xml)
    info = ""
    items = root.xpath("//*[local-name()='procedimentoExecutado']")
    if mutation in {0, 4}:
        items[0].xpath("./*[local-name()='valorTotal']")[0].text = "999.00"
    if mutation == 1:
        root.xpath("//*[local-name()='valorTotalGeral']")[0].text = "1.00"
    elif mutation == 2:
        root.xpath("//*[local-name()='epilogo']/*[local-name()='hash']")[0].text = "0" * 32
    elif mutation == 3:
        items[1].xpath("./*[local-name()='sequencialItem']")[0].text = "1"
    elif mutation == 4:
        root.xpath("//*[local-name()='epilogo']/*[local-name()='hash']")[0].text = "0" * 32
    elif mutation == 5:
        item = items[0]
        item.xpath("./*[local-name()='valorUnitario']")[0].text = "0.00"
        item.xpath("./*[local-name()='valorTotal']")[0].text = "0.00"
        info = "O valor unitário contratado é R$ 125,00."
    elif mutation == 6:
        root.xpath("//*[local-name()='numeroCarteira']")[0].getparent().remove(
            root.xpath("//*[local-name()='numeroCarteira']")[0]
        )
        info = "O número da carteira correto é 000000000001."
    return _xml_text(etree.tostring(root)), info


def _correction_tasks() -> list[dict[str, Any]]:
    tasks = []
    for index in range(7):
        lote = _new_lote(1, [2] if index == 3 else [1])
        xml = _xml_lote(lote)
        incorrect, info = _mutated_lote(xml, index)
        extra = f"{info}\n\n" if info else ""
        instruction = (
            "A operadora rejeitou o lote TISS 4.03.00 abaixo. Corrija-o sem alterar dados "
            "clínicos ou financeiros informados (carteira, procedimentos, quantidades, "
            "valores unitários) e devolva o XML completo corrigido, com o hash do epílogo "
            f"correto.\n\n{extra}Lote:\n{incorrect}\n\nResposta: apenas o XML."
        )
        tasks.append(
            _task(
                f"corrigir-{index + 1:02d}",
                "corrigir",
                "operadora" if index == 6 else "prestador",
                instruction,
                "xml",
                _expected_lote(xml),
                _xml_text(xml),
                incorrect,
            )
        )
    return tasks


def _hash_tasks() -> list[dict[str, Any]]:
    tasks = []
    for index, guide_count in enumerate((1, 2, 3, 1, 2, 3), start=1):
        xml = _xml_lote(_new_lote(guide_count))
        if index == 6:
            root = _parse_xml(xml)
            root.xpath("//*[local-name()='epilogo']/*[local-name()='hash']")[0].text = ""
            xml = etree.tostring(root, xml_declaration=True, encoding="ISO-8859-1")
        correct_hash = voa_tiss.hash_epilogo(xml)
        wrong_hash = hashlib.md5(_xml_text(xml).encode("utf-8")).hexdigest()
        gestor = index > 3
        prompt = (
            "Você audita lotes recebidos. O hash do epílogo do lote abaixo pode estar "
            "adulterado. Calcule o hash correto (MD5 conforme o padrão TISS)."
            if gestor
            else "Calcule o hash do epílogo (MD5 conforme o padrão TISS) do lote TISS abaixo."
        )
        tasks.append(
            _task(
                f"hash-{index:02d}",
                "hash",
                "gestor" if gestor else "prestador",
                f"{prompt}\n\nLote:\n{_xml_text(xml)}\n\n"
                "Resposta: apenas o hash em hexadecimal minúsculo.",
                "texto",
                {"hash": correct_hash},
                correct_hash,
                wrong_hash,
            )
        )
    return tasks


def _send_statement(
    lote: dict[str, Any],
    scenario: str,
    *,
    partial: bool = False,
) -> bytes:
    xml = _xml_lote(lote)
    sent = sandbox.enviar_lote(xml, cenario=scenario)
    if not sent["aceito"] or not sent["protocolo"]:
        raise ValueError("A operadora simulada não aceitou o lote")
    root = _parse_xml(sandbox.demonstrativo(sent["protocolo"]))
    details = root.xpath("//*[local-name()='detalhesGuia']")
    fallback_codes = tuple(code for code in _TABLE38_CODES if glosa(code) is not None)
    if not fallback_codes:
        raise ValueError("A Tabela 38 não contém códigos de glosa disponíveis")
    replacement_index = 0
    updated_reasons: set[int] = set()
    for detail in details:
        glosa_node = detail.xpath("./*[local-name()='relacaoGlosa']")
        if not glosa_node:
            continue
        code_element = glosa_node[0].xpath("./*[local-name()='tipoGlosa']")[0]
        code = (code_element.text or "").strip()
        if glosa(code) is None:
            code = fallback_codes[replacement_index % len(fallback_codes)]
            replacement_index += 1
            code_element.text = code
        official = glosa(code)
        if official is None:
            raise ValueError(f"Código de glosa indisponível: {code}")
        guide = detail.getparent()
        if guide is not None and id(guide) not in updated_reasons:
            reason = guide.xpath("./*[local-name()='motivoGlosaGuia']")
            if reason:
                reason[0].xpath("./*[local-name()='codigoGlosa']")[0].text = code
                reason[0].xpath("./*[local-name()='descricaoGlosa']")[0].text = official[
                    "descricao"
                ]
                updated_reasons.add(id(guide))
        if partial:
            informed = Decimal(detail.xpath("./*[local-name()='valorInformado']")[0].text or "0")
            partial_amount = informed / 2
            detail.xpath("./*[local-name()='valorLiberado']")[0].text = f"{partial_amount:.2f}"
            glosa_node[0].xpath("./*[local-name()='valorGlosa']")[0].text = f"{partial_amount:.2f}"
    for guide in root.xpath("//*[local-name()='relacaoGuias']"):
        rows = guide.xpath("./*[local-name()='detalhesGuia']")
        released = sum(
            Decimal(row.xpath("./*[local-name()='valorLiberado']")[0].text or "0") for row in rows
        )
        glosa_total = sum(
            Decimal(node.xpath("./*[local-name()='valorGlosa']")[0].text or "0")
            for row in rows
            for node in row.xpath("./*[local-name()='relacaoGlosa']")
        )
        for name, value in (
            ("valorLiberadoGuia", released),
            ("valorGlosaGuia", glosa_total),
        ):
            guide.xpath(f"./*[local-name()='{name}']")[0].text = f"{value:.2f}"
    protocols = root.xpath("//*[local-name()='dadosProtocolo']")
    for protocol in protocols:
        guides = protocol.xpath("./*[local-name()='relacaoGuias']")
        released = sum(
            Decimal(guide.xpath("./*[local-name()='valorLiberadoGuia']")[0].text or "0")
            for guide in guides
        )
        glosa_total = sum(
            Decimal(guide.xpath("./*[local-name()='valorGlosaGuia']")[0].text or "0")
            for guide in guides
        )
        for name, value in (
            ("valorLiberadoProtocolo", released),
            ("valorGlosaProtocolo", glosa_total),
            ("valorLiberadoGeral", released),
            ("valorGlosaGeral", glosa_total),
        ):
            node = root.xpath(f"//*[local-name()='{name}']")
            if node:
                node[0].text = f"{value:.2f}"
    return _write_hash(root)


def _statement_expected(xml: bytes) -> dict[str, Any]:
    parse_demonstrativo(xml)
    root = _parse_xml(xml)
    result = []
    for guide in root.xpath("//*[local-name()='relacaoGuias']"):
        guide_number = guide.xpath("./*[local-name()='numeroGuiaPrestador']")[0].text or ""
        for detail in guide.xpath("./*[local-name()='detalhesGuia']"):
            relations = detail.xpath("./*[local-name()='relacaoGlosa']")
            if not relations:
                continue
            relation = relations[0]
            amount = Decimal(relation.xpath("./*[local-name()='valorGlosa']")[0].text or "0")
            if amount <= 0:
                continue
            code = relation.xpath("./*[local-name()='tipoGlosa']")[0].text or ""
            official = glosa(code)
            if official is None:
                raise ValueError(f"Código de glosa indisponível: {code}")
            result.append(
                {
                    "guia": guide_number,
                    "sequencial": detail.xpath("./*[local-name()='sequencialItem']")[0].text or "",
                    "codigo": code,
                    "descricao": official["descricao"],
                    "valor_glosa_centavos": int(amount * 100),
                }
            )
    return {"itens": result}


def _glosa_tasks() -> list[dict[str, Any]]:
    tasks = []
    for index, code in enumerate(_TABLE38_CODES, start=1):
        result = glosa(code)
        if result is None:
            raise ValueError(f"Código de glosa indisponível: {code}")
        reference = _json({"codigo": code, "descricao": result["descricao"]})
        wrong_code = next(
            candidate
            for candidate in _TABLE38_CODES
            if candidate != code and glosa(candidate) is not None
        )
        wrong_description = glosa(wrong_code)
        if wrong_description is None:
            raise ValueError(f"Código de glosa indisponível: {wrong_code}")
        wrong = _json({"codigo": code, "descricao": wrong_description["descricao"]})
        tasks.append(
            _task(
                f"glosa-codigo-{index:02d}",
                "glosa",
                "profissional",
                f"Um convênio glosou seu atendimento com o código {code} da Tabela 38 "
                "da TISS (mensagens de glosa). Qual é a descrição oficial desse código?\n\n"
                f'Resposta: JSON {{"codigo": "{code}", "descricao": '
                f'"{result["descricao"]}"}}.',
                "json",
                {"codigo": code, "descricao": result["descricao"]},
                reference,
                wrong,
            )
        )
    scenarios = (
        (1, [1], "carteirinha_vencida", False),
        (2, [1, 1], "sem_autorizacao", False),
        (1, [2], "duplicidade", False),
        (1, [1], "carteirinha_vencida", True),
    )
    for index, (guide_count, item_counts, scenario, partial) in enumerate(scenarios, start=1):
        statement = _send_statement(_new_lote(guide_count, item_counts), scenario, partial=partial)
        expected = _statement_expected(statement)
        if not expected["itens"]:
            raise ValueError("O demonstrativo sintético não contém glosa")
        wrong = copy.deepcopy(expected)
        wrong_code = next(
            candidate
            for candidate in _TABLE38_CODES
            if candidate != wrong["itens"][0]["codigo"] and glosa(candidate) is not None
        )
        wrong["itens"][0]["codigo"] = wrong_code
        wrong_description = glosa(wrong_code)
        if wrong_description is None:
            raise ValueError(f"Código de glosa indisponível: {wrong_code}")
        wrong["itens"][0]["descricao"] = wrong_description["descricao"]
        sample_code = expected["itens"][0]["codigo"]
        instruction = (
            "Você recebeu o demonstrativo de análise de conta abaixo, referente aos seus "
            "atendimentos. Liste cada item glosado com a guia, o sequencial do item, o código "
            "e a descrição oficial da glosa na Tabela 38 da TISS e o valor glosado.\n\n"
            f"Demonstrativo:\n{statement.decode('ISO-8859-1')}\n\nResposta: JSON "
            '{"itens": [{"guia": "0001", "sequencial": "1", '
            f'"codigo": "{sample_code}", "descricao": "...", '
            '"valor_glosa": "100.00"}]} (lista vazia se nada foi glosado).'
        )
        tasks.append(
            _task(
                f"glosa-demonstrativo-{index:02d}",
                "glosa",
                "paciente",
                instruction,
                "json",
                expected,
                _json(
                    {
                        "itens": [
                            {
                                "guia": item["guia"],
                                "sequencial": item["sequencial"],
                                "codigo": item["codigo"],
                                "descricao": item["descricao"],
                                "valor_glosa": f"{item['valor_glosa_centavos'] // 100}."
                                f"{item['valor_glosa_centavos'] % 100:02d}",
                            }
                            for item in expected["itens"]
                        ]
                    }
                ),
                _json(
                    {
                        "itens": [
                            {
                                "guia": item["guia"],
                                "sequencial": item["sequencial"],
                                "codigo": item["codigo"],
                                "descricao": item["descricao"],
                                "valor_glosa": f"{item['valor_glosa_centavos'] // 100}."
                                f"{item['valor_glosa_centavos'] % 100:02d}",
                            }
                            for item in wrong["itens"]
                        ]
                    }
                ),
            )
        )
    return tasks


def _reconciliation_expected(xml: bytes) -> dict[str, Any]:
    decisions = parse_demonstrativo(xml)
    guides = {}
    for decision in decisions:
        guides[decision.guia_ref] = {
            "decisao": decision.decision,
            "valor_liberado_centavos": decision.valor_liberado_cents,
            "valor_glosa_centavos": decision.valor_glosa_cents,
        }
    return {"guias": guides}


def _totals_expected(xml: bytes) -> dict[str, Any]:
    decisions = parse_demonstrativo(xml)
    return {
        "totais": {
            "valor_liberado": sum(item.valor_liberado_cents for item in decisions),
            "valor_glosa": sum(item.valor_glosa_cents for item in decisions),
        }
    }


def _reconciliation_tasks() -> list[dict[str, Any]]:
    tasks = []
    cases = (
        (2, [1, 1], "aprovado", False),
        (2, [1, 1], "duplicidade", False),
        (1, [1], "carteirinha_vencida", True),
        (2, [1, 1], "sem_autorizacao", False),
    )
    for index, (guide_count, item_counts, scenario, partial) in enumerate(cases, start=1):
        lote = _new_lote(guide_count, item_counts)
        xml_lote = _xml_lote(lote)
        statement = _send_statement(lote, scenario, partial=partial)
        expected = _reconciliation_expected(statement)
        wrong = copy.deepcopy(expected)
        first_guide = next(iter(wrong["guias"].values()))
        first_guide["decisao"] = "pago" if first_guide["decisao"] != "pago" else "glosado"
        reference_data = {
            "guias": {
                number: {
                    "decisao": row["decisao"],
                    "valor_liberado": f"{row['valor_liberado_centavos'] // 100}."
                    f"{row['valor_liberado_centavos'] % 100:02d}",
                    "valor_glosa": f"{row['valor_glosa_centavos'] // 100}."
                    f"{row['valor_glosa_centavos'] % 100:02d}",
                }
                for number, row in expected["guias"].items()
            }
        }
        wrong_data = copy.deepcopy(reference_data)
        wrong_data["guias"][next(iter(wrong_data["guias"]))]["decisao"] = first_guide["decisao"]
        instruction = (
            "Concilie o demonstrativo de análise de conta abaixo com o lote enviado: para "
            'cada guia, informe a decisão da operadora ("pago", "glosado" ou '
            '"glosa_parcial"), o valor liberado e o valor glosado.\n\n'
            f"Lote enviado:\n{_xml_text(xml_lote)}\n\n"
            f"Demonstrativo:\n{statement.decode('ISO-8859-1')}\n\n"
            'Resposta: JSON {"guias": {"<número da guia do prestador>": '
            '{"decisao": "...", "valor_liberado": "0.00", '
            '"valor_glosa": "0.00"}}}.'
        )
        tasks.append(
            _task(
                f"conciliar-guia-{index:02d}",
                "conciliar",
                "prestador",
                instruction,
                "json",
                expected,
                _json(reference_data),
                _json(wrong_data),
            )
        )
    for index, (guide_count, scenario) in enumerate(
        ((2, "carteirinha_vencida"), (2, "sem_autorizacao")), start=1
    ):
        statement = _send_statement(_new_lote(guide_count), scenario, partial=False)
        expected = _totals_expected(statement)
        wrong = {
            "valor_liberado": f"{expected['totais']['valor_liberado'] // 100}.00",
            "valor_glosa": f"{expected['totais']['valor_glosa'] // 100}.00",
        }
        wrong["valor_glosa"] = "999.99"
        reference_data = {
            "valor_liberado": f"{expected['totais']['valor_liberado'] // 100}."
            f"{expected['totais']['valor_liberado'] % 100:02d}",
            "valor_glosa": f"{expected['totais']['valor_glosa'] // 100}."
            f"{expected['totais']['valor_glosa'] % 100:02d}",
        }
        tasks.append(
            _task(
                f"conciliar-totais-{index:02d}",
                "conciliar",
                "gestor",
                "Você audita o faturamento. Some o valor liberado e o valor glosado de "
                f"todas as guias do demonstrativo abaixo.\n\nDemonstrativo:\n"
                f"{statement.decode('ISO-8859-1')}\n\nResposta: JSON "
                '{"valor_liberado": "0.00", "valor_glosa": "0.00"}.',
                "json",
                expected,
                _json(reference_data),
                _json(wrong),
            )
        )
    return tasks


def _rule_package(registry: str, *, strict: bool) -> dict[str, Any]:
    rules = [
        {
            "id": "registro.presente",
            "descricao": "O registro da operadora deve estar presente.",
            "source": {
                "url": "https://example.org/regras",
                "titulo": "Regra sintética",
                "data": "2026-01-01",
                "acesso": "publico",
            },
            "severity": "error",
            "check": {"tipo": "obrigatorio", "pointer": "/operadora/registro_ans"},
        },
        {
            "id": "registro.permitido",
            "descricao": "O registro deve estar na lista informada.",
            "source": {
                "url": "https://example.org/regras",
                "titulo": "Regra sintética",
                "data": "2026-01-01",
                "acesso": "publico",
            },
            "severity": "error",
            "check": {
                "tipo": "valores",
                "pointer": "/operadora/registro_ans",
                "permitidos": [registry if not strict else "000000"],
            },
        },
        {
            "id": "lote.formato",
            "descricao": "O número do lote deve seguir o padrão informado.",
            "source": {
                "url": "https://example.org/regras",
                "titulo": "Regra sintética",
                "data": "2026-01-01",
                "acesso": "publico",
            },
            "severity": "error",
            "check": {"tipo": "padrao", "pointer": "/numero_lote", "regex": "^TISS-.*$"},
        },
        {
            "id": "guias.limite",
            "descricao": "O lote deve respeitar o limite de guias.",
            "source": {
                "url": "https://example.org/regras",
                "titulo": "Regra sintética",
                "data": "2026-01-01",
                "acesso": "publico",
            },
            "severity": "error",
            "check": {"tipo": "max_itens", "pointer": "/guias", "max": 1 if strict else 0},
        },
    ]
    if strict:
        rules.append(
            {
                "id": "campo.obrigatorio",
                "descricao": "O campo exigido deve estar presente.",
                "source": {
                    "url": "https://example.org/regras",
                    "titulo": "Regra sintética",
                    "data": "2026-01-01",
                    "acesso": "publico",
                },
                "severity": "error",
                "check": {"tipo": "obrigatorio", "pointer": "/campo_ausente"},
            }
        )
    return {
        "operadora": registry,
        "mantenedor": {"tipo": "comunidade"},
        "official": False,
        "versao_tiss": "4.03.00",
        "regras": rules,
    }


def _rule_tasks() -> list[dict[str, Any]]:
    tasks = []
    for index, strict in enumerate((False, True), start=1):
        lote = _new_lote(2 if strict else 1)
        package = _rule_package("123456", strict=strict)
        report = voa_tiss.check(lote, operadora=package)
        expected = {
            "regras": sorted(
                finding.rule["id"] for finding in report.findings if finding.rule is not None
            )
        }
        wrong = [*expected["regras"], "regra.inexistente"]
        instruction = (
            "Você é a operadora 123456 e aplica o pacote de regras próprio abaixo (JSON) "
            "ao lote recebido (JSON do voa-tiss). Quais regras o lote viola?\n\n"
            f"Pacote de regras:\n{_json(package)}\n\nLote:\n{_json(lote)}\n\n"
            "Resposta: JSON com a lista dos ids das regras violadas, ex.: "
            '["id.a", "id.b"] (lista vazia se nenhuma).'
        )
        tasks.append(
            _task(
                f"regra-pacote-{index:02d}",
                "regra",
                "operadora",
                instruction,
                "json",
                expected,
                _json(expected["regras"]),
                _json(wrong),
            )
        )
    for index, authorized in enumerate((False, True), start=1):
        lote = _new_lote(1)
        guide = lote["guias"][0]
        number = guide["cabecalho_guia"]["numero_guia_prestador"]
        code = guide["procedimentos_executados"][0]["procedimento"]["codigo_procedimento"]
        authorizations = {number: {"validade": "2026-12-31"}} if authorized else {}
        context = {
            "tabela_operadora": {"exige_autorizacao": [code]},
            "autorizacoes": authorizations,
        }
        report = audit(lote, contexto=context)
        answer = (
            "sim"
            if any(finding.code == "audit.autorizacao_ausente" for finding in report.findings)
            else "nao"
        )
        instruction = (
            "Você é o profissional executante. A operadora exige autorização prévia para "
            f"os procedimentos {code}. Veja a guia abaixo e as autorizações já emitidas. "
            "Falta autorização para esta guia?\n\n"
            f"Autorizações emitidas: {_json(authorizations)}\n\n"
            f"Guia (JSON do voa-tiss):\n{_json(guide)}\n\n"
            'Resposta: apenas "sim" ou "não".'
        )
        tasks.append(
            _task(
                f"regra-autorizacao-{index:02d}",
                "regra",
                "profissional",
                instruction,
                "texto",
                {"resposta": answer},
                answer,
                "não" if answer == "sim" else "sim",
            )
        )
    for index, (table, name, term, code) in enumerate(
        (
            ("76", "Pronto-socorro", "atendimento de urgência", "04"),
            ("50", "Exame", "exame", "23"),
        ),
        start=1,
    ):
        if not dominio.lookup(table, code):
            raise ValueError(f"Código de domínio indisponível: {table}/{code}")
        instruction = (
            "Na TISS 4.03.00, qual é o código da Tabela de domínio "
            f'{table} ({name}) para "{term}"?\n\nResposta: apenas o código.'
        )
        tasks.append(
            _task(
                f"regra-dominio-{index:02d}",
                "regra",
                "gestor",
                instruction,
                "texto",
                {"tabela": table, "codigo": code},
                code,
                "99",
            )
        )
    return tasks


def gerar() -> list[dict[str, Any]]:
    """Gere os dados determinísticos de todas as tarefas."""
    tasks = (
        _generation_tasks()
        + _correction_tasks()
        + _hash_tasks()
        + _glosa_tasks()
        + _reconciliation_tasks()
        + _rule_tasks()
    )
    return sorted(tasks, key=lambda task: task["id"])


def escrever(destination: Path = TASK_DIR) -> list[dict[str, Any]]:
    """Grave os arquivos das tarefas e remova arquivos obsoletos."""
    tasks = gerar()
    destination.mkdir(parents=True, exist_ok=True)
    names = set()
    for task in tasks:
        path = destination / f"{task['id']}.json"
        path.write_text(_json(task) + "\n", encoding="utf-8")
        names.add(path.name)
    for path in destination.glob("*.json"):
        if path.name not in names:
            path.unlink()
    return tasks


__all__ = ["escrever", "gerar"]
