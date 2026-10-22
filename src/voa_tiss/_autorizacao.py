"""Decisão determinística para solicitações de autorização SP/SADT."""

from __future__ import annotations

from typing import Any

from ._audit_rules import _day, _matches
from ._autorizacao_xml import AutorizacaoError, _xml_bytes, build_autorizacao, parse_autorizacao
from ._report import Finding, Report
from ._rules import _package, validate_package
from ._validate import validate
from .codes import CODE_CATALOG


def _finding(
    code: str,
    message: str,
    pointer: str | None = None,
    *,
    rule: dict[str, Any] | None = None,
    needs: list[str] | None = None,
) -> Finding:
    spec = CODE_CATALOG[code]
    if needs is None and spec["needs"] == "pointer":
        needs = [pointer or "/solicitacao"]
    return Finding(
        code=code,
        severity=spec["severity"],
        guia=None,
        xpath=None,
        pointer=pointer,
        message=message,
        fix=None,
        needs=needs,
        glosa=spec["glosa"],
        rule=rule,
    )


def _required(message: dict[str, Any]) -> list[str]:
    missing: list[str] = []

    def field(value: Any, key: str, pointer: str) -> Any:
        if not isinstance(value, dict) or value.get(key) in (None, ""):
            missing.append(pointer)
            return None
        return value[key]

    for key in ("versao", "transacao", "prestador", "operadora"):
        field(message, key, f"/{key}")
    transaction = message.get("transacao")
    if isinstance(transaction, dict):
        for key in (
            "sequencial_transacao",
            "data_registro_transacao",
            "hora_registro_transacao",
        ):
            field(transaction, key, f"/transacao/{key}")
    provider = message.get("prestador")
    if isinstance(provider, dict) and not any(
        provider.get(key) for key in ("codigo_prestador_na_operadora", "cnpj", "cpf")
    ):
        missing.append("/prestador")
    plan = message.get("operadora")
    if isinstance(plan, dict):
        field(plan, "registro_ans", "/operadora/registro_ans")
    body = message.get("solicitacao")
    if not isinstance(body, dict):
        missing.append("/solicitacao")
        return missing

    header = field(body, "cabecalho_solicitacao", "/solicitacao/cabecalho_solicitacao")
    if isinstance(header, dict):
        field(header, "registro_ans", "/solicitacao/cabecalho_solicitacao/registro_ans")
        field(
            header,
            "numero_guia_prestador",
            "/solicitacao/cabecalho_solicitacao/numero_guia_prestador",
        )
    for key in (
        "tipo_etapa_autorizacao",
        "dados_beneficiario",
        "dados_solicitante",
        "carater_atendimento",
        "data_solicitacao",
        "procedimentos_solicitados",
    ):
        field(body, key, f"/solicitacao/{key}")

    beneficiary = body.get("dados_beneficiario")
    if isinstance(beneficiary, dict):
        field(
            beneficiary,
            "numero_carteira",
            "/solicitacao/dados_beneficiario/numero_carteira",
        )
        field(beneficiary, "atendimento_rn", "/solicitacao/dados_beneficiario/atendimento_rn")
    requester = body.get("dados_solicitante")
    if isinstance(requester, dict):
        contracted = requester.get("contratado_solicitante")
        if not isinstance(contracted, dict) or not any(
            contracted.get(key)
            for key in ("codigo_prestador_na_operadora", "cpf_contratado", "cnpj_contratado")
        ):
            missing.append("/solicitacao/dados_solicitante/contratado_solicitante")
        professional = requester.get("profissional_solicitante")
        if not isinstance(professional, dict):
            missing.append("/solicitacao/dados_solicitante/profissional_solicitante")
        else:
            for key in (
                "conselho_profissional",
                "numero_conselho_profissional",
                "uf",
                "cbos",
            ):
                field(
                    professional,
                    key,
                    f"/solicitacao/dados_solicitante/profissional_solicitante/{key}",
                )
        field(
            requester,
            "nome_contratado_solicitante",
            "/solicitacao/dados_solicitante/nome_contratado_solicitante",
        )
    items = body.get("procedimentos_solicitados")
    if isinstance(items, list):
        if not items:
            missing.append("/solicitacao/procedimentos_solicitados")
        for index, item in enumerate(items):
            procedure = field(
                item,
                "procedimento",
                f"/solicitacao/procedimentos_solicitados/{index}/procedimento",
            )
            field(
                item,
                "quantidade_solicitada",
                f"/solicitacao/procedimentos_solicitados/{index}/quantidade_solicitada",
            )
            if isinstance(procedure, dict):
                for key in ("codigo_tabela", "codigo_procedimento", "descricao_procedimento"):
                    field(
                        procedure,
                        key,
                        f"/solicitacao/procedimentos_solicitados/{index}/procedimento/{key}",
                    )
    return sorted(set(missing))


def _rule_ref(package: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    source = dict(rule["source"])
    source["official"] = package["official"]
    return {
        "id": rule["id"],
        "source": source,
        "mantenedor": package["mantenedor"],
    }


def _carteirinha_finding(contexto: dict[str, Any], solicitacao: dict[str, Any]) -> Finding | None:
    cards = contexto.get("carteirinhas")
    body = solicitacao.get("solicitacao", {})
    header = body.get("cabecalho_solicitacao", {})
    number = str(header.get("numero_guia_prestador", ""))
    card = cards.get(number) if isinstance(cards, dict) else None
    if not isinstance(card, dict):
        return None
    pointer = "/solicitacao/dados_beneficiario/numero_carteira"
    if _matches("audit.carteirinha_inativa", card.get("ativa")):
        return _finding(
            "autorizacao.carteirinha",
            "Carteirinha inativa; encaminhar a solicitação para auditoria.",
            pointer,
        )
    expiry = _day(card.get("validade") or card.get("fim"))
    reference = _day(body.get("data_solicitacao"))
    if _matches("audit.carteirinha_vencida", (expiry, reference)):
        return _finding(
            "autorizacao.carteirinha",
            "Carteirinha vencida; encaminhar a solicitação para auditoria.",
            pointer,
        )
    return None


def check_autorizacao(
    solicitacao: dict[str, Any] | bytes | str,
    *,
    contexto: dict[str, Any] | None = None,
) -> Report:
    """Valida uma solicitação e retorna uma decisão determinística."""
    context = contexto or {}
    try:
        if isinstance(solicitacao, (bytes, str)):
            message = parse_autorizacao(solicitacao)
            xml = _xml_bytes(solicitacao)
        else:
            message = solicitacao
            if not isinstance(message, dict) or "solicitacao" not in message:
                raise AutorizacaoError("A mensagem deve conter uma solicitação SP/SADT")
            xml = build_autorizacao(message)
        if "solicitacao" not in message or "autorizacao" in message:
            raise AutorizacaoError("A mensagem deve conter uma solicitação SP/SADT")
        base = validate(xml)
    except (AutorizacaoError, TypeError, ValueError, UnicodeEncodeError) as exc:
        finding = _finding("lote.estrutura", f"Estrutura da solicitação inválida: {exc}.")
        return Report(
            False,
            "4.03.00",
            (finding,),
            {"tipo": "pendente", "rules": [], "needs": ["/solicitacao"]},
        )

    findings = list(base.findings)
    card_finding = _carteirinha_finding(context, message)
    if card_finding is not None:
        findings.append(card_finding)
    needs = _required(message)
    package = _package(context.get("operadora"))
    valid_package = package if package is not None and not validate_package(package) else None
    rules = (
        [rule for rule in valid_package["regras"] if rule["check"]["tipo"] == "exige_autorizacao"]
        if valid_package
        else []
    )
    refs = [_rule_ref(valid_package, rule) for rule in rules] if valid_package is not None else []
    if needs:
        decision_type = "pendente"
        findings.append(
            _finding(
                "autorizacao.dado_ausente",
                "Dados obrigatórios ausentes na solicitação.",
                needs=needs,
            )
        )
        if not rules:
            findings.append(
                _finding(
                    "autorizacao.sem_regra",
                    "Sem regra da operadora para decidir a autorização.",
                )
            )
    elif not rules:
        findings.append(
            _finding(
                "autorizacao.sem_regra",
                "Sem regra da operadora para decidir a autorização.",
            )
        )
        decision_type = "encaminhar_auditor"
    else:
        assert valid_package is not None
        has_audit = card_finding is not None
        has_pending = False
        body = message["solicitacao"]
        if not body.get("indicacao_clinica"):
            matched = any(
                str(item.get("procedimento", {}).get("codigo_procedimento", ""))
                in rule["check"]["codigos"]
                for rule in rules
                for item in body.get("procedimentos_solicitados", [])
                if isinstance(item, dict) and isinstance(item.get("procedimento"), dict)
            )
            if matched:
                has_pending = True
                needs = ["/solicitacao/indicacao_clinica"]
                findings.append(
                    _finding(
                        "autorizacao.dado_ausente",
                        "Indicação clínica necessária para analisar o procedimento.",
                        "/solicitacao/indicacao_clinica",
                        needs=needs,
                    )
                )
        for rule in rules:
            codes = rule["check"]["codigos"]
            for index, item in enumerate(body.get("procedimentos_solicitados", [])):
                procedure = item.get("procedimento", {}) if isinstance(item, dict) else {}
                code = str(procedure.get("codigo_procedimento", ""))
                if code not in codes or not body.get("indicacao_clinica"):
                    continue
                has_audit = True
                findings.append(
                    _finding(
                        "autorizacao.exige_auditoria",
                        f"Procedimento {code} exige autorização prévia pela regra {rule['id']}.",
                        f"/solicitacao/procedimentos_solicitados/{index}/procedimento/"
                        "codigo_procedimento",
                        rule=_rule_ref(valid_package, rule),
                    )
                )
        decision_type = (
            "pendente"
            if has_pending
            else "encaminhar_auditor"
            if has_audit
            else "aprovar_por_regra"
        )
    errors = any(finding.severity == "error" for finding in findings)
    if errors and decision_type != "pendente":
        decision_type = "pendente"
    if decision_type == "pendente" and not needs:
        needs = sorted(
            {
                finding.pointer or finding.xpath or "/solicitacao"
                for finding in findings
                if finding.severity == "error"
            }
        ) or ["/solicitacao"]
    return Report(
        not errors,
        base.version,
        tuple(findings),
        {"tipo": decision_type, "rules": refs, "needs": needs},
    )


__all__ = ["check_autorizacao"]
