"""Auditorias determinísticas de lotes TISS com contexto versionado."""

from __future__ import annotations

import datetime
from typing import Any, TypedDict

from ._audit_rules import _day, _matches, _money
from ._audit_schema import audit_context_schema
from ._lote import _procedure_records
from ._report import Finding, Report
from ._rules import rule_findings
from .codes import CODE_CATALOG
from .tuss import lookup


class AuditContext(TypedDict, total=False):
    tabela_operadora: dict[str, Any]
    carteirinhas: dict[str, Any]
    autorizacoes: dict[str, Any]


def _lookup_context(
    values: Any, *, guide_index: int, guide: dict[str, Any], field: str
) -> dict[str, Any] | None:
    if not isinstance(values, dict):
        return None
    number = str(
        guide.get("cabecalho_guia", {}).get("numero_guia_prestador")
        or guide.get("cabecalho_consulta", {}).get("numero_guia_prestador")
        or guide_index
    )
    result = values.get(number, values.get(str(guide_index)))
    if isinstance(result, dict):
        return result
    return None


def _finding(
    code: str,
    pointer: str | None,
    message: str,
    *,
    severity: str | None = None,
    needs: list[str] | None = None,
    glosa: str | None = None,
) -> Finding:
    spec = CODE_CATALOG[code]
    severity = severity or spec["severity"]
    glosa = glosa or spec["glosa"]
    if needs is None and spec["needs"] == "pointer":
        needs = [pointer or "/contexto"]
    return Finding(
        code=code,
        severity=severity,  # type: ignore[arg-type]
        guia=None,
        xpath=None,
        pointer=pointer,
        message=message,
        fix=None,
        needs=needs,
        glosa=glosa,
    )


def audit(
    lote: dict[str, Any],
    *,
    contexto: AuditContext | None = None,
    at: datetime.date | str | None = None,
    operadora: Any = None,
) -> Report:
    """Verifica regras locais e regras do contexto informado."""
    context = contexto or {}
    table = context.get("tabela_operadora", {})
    findings: list[Finding] = []
    guides = lote.get("guias", [])
    if _matches("lote.vazio", guides):
        findings.append(_finding("lote.vazio", "/guias", "O lote não contém guias."))
    max_guides = table.get("max_guias")
    if isinstance(max_guides, int) and _matches("lote.acima_do_teto", len(guides), max_guides):
        findings.append(
            _finding(
                "lote.acima_do_teto",
                "/guias",
                f"O lote contém {len(guides)} guias; o limite é {max_guides}.",
            )
        )
    procedures = table.get("procedimentos")
    if isinstance(procedures, list) and _matches("audit.tabela_sem_procedimentos", procedures):
        findings.append(
            _finding(
                "audit.tabela_sem_procedimentos", "/guias", "Tabela da operadora sem procedimentos."
            )
        )
    registry = table.get("registro_ans")
    if _matches(
        "audit.operadora_divergente",
        (registry, lote.get("operadora", {}).get("registro_ans")),
    ):
        findings.append(
            _finding(
                "audit.operadora_divergente",
                "/operadora/registro_ans",
                "Registro ANS diverge do contexto.",
            )
        )
    for index, guide in enumerate(guides):
        pointer = f"/guias/{index}"
        service_date = _day(guide.get("dados_atendimento", {}).get("data_atendimento"))
        if service_date is None:
            first_item: dict[str, Any] = next(iter(guide.get("procedimentos_executados", [])), {})
            if isinstance(first_item, dict):
                service_date = _day(first_item.get("data_execucao"))
        service_date = service_date or _day(
            guide.get("cabecalho_guia", {}).get("data_atendimento")
            or guide.get("cabecalho_consulta", {}).get("data_atendimento")
        )
        reference = service_date or _day(at)
        if table:
            inicio = _day(table.get("vigencia_inicio"))
            fim = _day(table.get("vigencia_fim"))
            if inicio or fim:
                if _matches("audit.data_ausente", reference):
                    findings.append(
                        _finding(
                            "audit.data_ausente",
                            f"{pointer}/dados_atendimento/data_atendimento",
                            "Data de atendimento necessária para verificar vigência da tabela.",
                            severity="warning",
                            needs=[f"{pointer}/dados_atendimento/data_atendimento"],
                        )
                    )
                elif _matches("audit.tabela_fora_de_vigencia", (reference, inicio, fim)):
                    findings.append(
                        _finding(
                            "audit.tabela_fora_de_vigencia",
                            f"{pointer}/dados_atendimento/data_atendimento",
                            "Data do atendimento fora da vigência da tabela.",
                        )
                    )
        guide_registry = guide.get("cabecalho_guia", {}).get("registro_ans") or guide.get(
            "cabecalho_consulta", {}
        ).get("registro_ans")
        lot_registry = lote.get("operadora", {}).get("registro_ans")
        if _matches("audit.operadora_divergente", (guide_registry, lot_registry)):
            findings.append(
                _finding(
                    "audit.operadora_divergente",
                    f"{pointer}/cabecalho_guia/registro_ans",
                    "Registro ANS da guia diverge do cabeçalho do lote.",
                )
            )
        for relative, procedure, amount_value, item_date in _procedure_records(guide):
            code = str(procedure.get("codigo_procedimento", ""))
            table_code = str(procedure.get("codigo_tabela", ""))
            procedure_pointer = pointer + relative
            reference = _day(item_date) or service_date or _day(at)
            if _matches("audit.procedimento_ausente", code):
                findings.append(
                    _finding(
                        "audit.procedimento_ausente",
                        procedure_pointer + "/codigo_procedimento",
                        "Código do procedimento ausente.",
                    )
                )
                continue
            records = (
                lookup(code, tabela=table_code, include_expired=True)
                if table_code in {"18", "19", "20", "22"}
                else []
            )
            if (
                not records
                and table_code in {"18", "19", "20", "22"}
                and _matches("tuss.inexistente", records)
            ):
                findings.append(
                    _finding(
                        "tuss.inexistente",
                        procedure_pointer + "/codigo_procedimento",
                        f"Código TUSS {code} inexistente na tabela {table_code}.",
                    )
                )
            elif records:
                if _matches("audit.data_ausente", reference) and any(
                    row.get("vigencia_inicio") or row.get("vigencia_fim") for row in records
                ):
                    findings.append(
                        _finding(
                            "audit.data_ausente",
                            pointer + "/dados_atendimento/data_atendimento",
                            "Data necessária para verificar vigência do código TUSS.",
                            severity="warning",
                            needs=[pointer + "/dados_atendimento/data_atendimento"],
                        )
                    )
                elif _matches("tuss.fora_de_vigencia", (records, reference)):
                    findings.append(
                        _finding(
                            "tuss.fora_de_vigencia",
                            procedure_pointer + "/codigo_procedimento",
                            f"Código TUSS {code} fora de vigência na data do atendimento.",
                        )
                    )
            if isinstance(procedures, list) and _matches(
                "audit.procedimento_fora_da_tabela",
                code,
                {str(item) for item in procedures},
            ):
                findings.append(
                    _finding(
                        "audit.procedimento_fora_da_tabela",
                        procedure_pointer + "/codigo_procedimento",
                        f"Procedimento {code} não consta na tabela da operadora.",
                    )
                )
            required = table.get("exige_autorizacao", [])
            if _matches("autorizacao_requerida", code, required):
                authorization = _lookup_context(
                    context.get("autorizacoes"),
                    guide_index=index,
                    guide=guide,
                    field="autorizacoes",
                )
                if _matches("audit.autorizacao_ausente", authorization):
                    findings.append(
                        _finding(
                            "audit.autorizacao_ausente",
                            pointer + "/dados_autorizacao",
                            "Autorização necessária não informada.",
                        )
                    )
                else:
                    assert authorization is not None
                    expiry = _day(authorization.get("validade"))
                    if _matches("audit.autorizacao_vencida", (expiry, reference)):
                        findings.append(
                            _finding(
                                "audit.autorizacao_vencida",
                                pointer + "/dados_autorizacao",
                                "Autorização vencida na data do atendimento.",
                            )
                        )
                    elif expiry and _matches("audit.data_ausente", reference):
                        findings.append(
                            _finding(
                                "audit.data_ausente",
                                pointer + "/dados_atendimento/data_atendimento",
                                "Data necessária para verificar validade da autorização.",
                                severity="warning",
                                needs=[pointer + "/dados_atendimento/data_atendimento"],
                            )
                        )
            amount = _money(amount_value)
            if _matches("audit.valor_nao_positivo", amount):
                findings.append(
                    _finding(
                        "audit.valor_nao_positivo",
                        procedure_pointer
                        + (
                            "/valor_total"
                            if guide.get("tipo") == "sp_sadt"
                            else "/valor_procedimento"
                        ),
                        "O valor do procedimento deve ser positivo.",
                    )
                )
        card_context = _lookup_context(
            context.get("carteirinhas"), guide_index=index, guide=guide, field="carteirinhas"
        )
        if context.get("carteirinhas") is not None:
            if _matches("audit.carteirinha_ausente", card_context):
                findings.append(
                    _finding(
                        "audit.carteirinha_ausente",
                        pointer + "/dados_beneficiario/numero_carteira",
                        "Carteirinha não localizada no contexto da operadora.",
                    )
                )
            else:
                assert card_context is not None
                if _matches("audit.carteirinha_inativa", card_context.get("ativa")):
                    findings.append(
                        _finding(
                            "audit.carteirinha_inativa",
                            pointer + "/dados_beneficiario/numero_carteira",
                            "Carteirinha inativa.",
                        )
                    )
                expiry = _day(card_context.get("validade") or card_context.get("fim"))
                if expiry and _matches("audit.data_ausente", reference):
                    findings.append(
                        _finding(
                            "audit.data_ausente",
                            pointer + "/dados_atendimento/data_atendimento",
                            "Data necessária para verificar validade da carteirinha.",
                            severity="warning",
                            needs=[pointer + "/dados_atendimento/data_atendimento"],
                        )
                    )
                elif _matches("audit.carteirinha_vencida", (expiry, reference)):
                    findings.append(
                        _finding(
                            "audit.carteirinha_vencida",
                            pointer + "/dados_beneficiario/numero_carteira",
                            "Carteirinha vencida na data do atendimento.",
                        )
                    )
    if operadora is not None:
        findings.extend(rule_findings(lote, operadora))
    unique: dict[tuple[Any, ...], Finding] = {}
    for finding in findings:
        unique[(finding.code, finding.guia, finding.pointer)] = finding
    result = tuple(
        sorted(
            unique.values(),
            key=lambda item: (item.pointer is None, item.pointer or "", item.code, item.message),
        )
    )
    return Report(not any(item.severity == "error" for item in result), "4.03.00", result)


__all__ = ["AuditContext", "audit", "audit_context_schema"]
