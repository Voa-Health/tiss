from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tiss import apply_fixes, audit, build_lote, check, parse_lote


def test_round_trip(valid_lote):
    xml = build_lote(valid_lote)
    assert parse_lote(xml) == valid_lote


FIXTURE_DIR = Path(__file__).parent / "fixtures/lotes"
FIXTURE_CASES = sorted(FIXTURE_DIR.glob("corrigivel-*.json")) + sorted(
    FIXTURE_DIR.glob("nao-corrigivel-*.json")
)


@pytest.mark.parametrize("path", FIXTURE_CASES, ids=lambda path: path.stem)
def test_fix_convergence_and_needs_fixtures(path):
    lote = json.loads(path.read_text(encoding="utf-8"))
    first = check(lote)
    if path.name.startswith("nao-corrigivel-"):
        finding = next(item for item in first.findings if item.needs)
        assert finding.fix is None
        return
    finding = next(item for item in first.findings if item.code == "item.valor_divergente")
    assert finding.fix[0]["op"] == "test"
    assert finding.fix[1]["op"] == "replace"
    corrected = apply_fixes(lote, first)
    final = check(corrected)
    assert final.valid and final.findings == ()


AUDIT_CODES = [
    "audit.procedimento_ausente",
    "audit.procedimento_fora_da_tabela",
    "audit.carteirinha_ausente",
    "audit.carteirinha_inativa",
    "audit.carteirinha_vencida",
    "audit.autorizacao_ausente",
    "audit.autorizacao_vencida",
    "audit.tabela_fora_de_vigencia",
    "audit.operadora_divergente",
    "audit.valor_nao_positivo",
    "audit.tabela_sem_procedimentos",
    "audit.data_ausente",
    "lote.vazio",
    "lote.acima_do_teto",
    "tuss.inexistente",
    "tuss.fora_de_vigencia",
]


def _audit_input(code, lote):
    guide = lote["guias"][0] if lote["guias"] else {}
    items = guide.get("procedimentos_executados", [])
    item = items[0] if items else {}
    procedure = item.get("procedimento", {})
    procedure_code = str(procedure.get("codigo_procedimento", ""))
    guide_number = str(
        guide.get("cabecalho_guia", {}).get("numero_guia_prestador")
        or guide.get("cabecalho_consulta", {}).get("numero_guia_prestador")
        or "0"
    )
    context = {}
    at = None
    if code == "audit.procedimento_ausente":
        procedure["codigo_procedimento"] = ""
    elif code == "audit.procedimento_fora_da_tabela":
        context = {"tabela_operadora": {"procedimentos": ["inexistente"]}}
    elif code == "audit.carteirinha_ausente":
        context = {"carteirinhas": {}}
    elif code == "audit.carteirinha_inativa":
        context = {"carteirinhas": {guide_number: {"ativa": False}}}
    elif code == "audit.carteirinha_vencida":
        context = {"carteirinhas": {guide_number: {"validade": "1900-01-01"}}}
    elif code in {"audit.autorizacao_ausente", "audit.autorizacao_vencida"}:
        context = {"tabela_operadora": {"exige_autorizacao": [procedure_code]}}
        if code == "audit.autorizacao_vencida":
            context["autorizacoes"] = {guide_number: {"validade": "1900-01-01"}}
    elif code == "audit.tabela_fora_de_vigencia":
        context = {"tabela_operadora": {"vigencia_inicio": "2099-01-01"}}
    elif code == "audit.operadora_divergente":
        context = {"tabela_operadora": {"registro_ans": "000000"}}
    elif code == "audit.valor_nao_positivo":
        item["valor_total"] = 0
    elif code == "audit.tabela_sem_procedimentos":
        context = {"tabela_operadora": {"procedimentos": []}}
    elif code in {"audit.data_ausente", "tuss.fora_de_vigencia"}:
        guide.get("dados_atendimento", {}).pop("data_atendimento", None)
        guide.get("cabecalho_guia", {}).pop("data_atendimento", None)
        guide.get("cabecalho_consulta", {}).pop("data_atendimento", None)
        for row in items:
            row.pop("data_execucao", None)
        if code == "audit.data_ausente":
            context = {"carteirinhas": {guide_number: {"validade": "2099-01-01"}}}
        else:
            at = "1900-01-01"
    elif code == "lote.vazio":
        lote["guias"] = []
    elif code == "lote.acima_do_teto":
        lote["guias"].append(deepcopy(guide))
        context = {"tabela_operadora": {"max_guias": len(lote["guias"]) - 1}}
    elif code == "tuss.inexistente":
        procedure["codigo_procedimento"] = "99999999"
    return context, at


@pytest.mark.parametrize("code", AUDIT_CODES)
def test_audit_rule_cases(valid_lote, code):
    assert code not in {finding.code for finding in audit(valid_lote).findings}
    lote = deepcopy(valid_lote)
    contexto, at = _audit_input(code, lote)
    report = audit(lote, contexto=contexto, at=at)
    finding = next(f for f in report.findings if f.code == code)
    assert finding.needs
