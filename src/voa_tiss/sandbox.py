"""Operadora simulada, sem persistência ou acesso à rede."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import zlib
from decimal import Decimal, InvalidOperation
from typing import Any

from lxml import etree

from ._autorizacao_xml import build_autorizacao, parse_autorizacao
from ._glosa import glosa
from ._lote_codec import hash_epilogo, parse_lote
from ._rules import _package, rule_findings
from ._schema import NS, parser
from ._validate import validate

_PREFIX = "vts_"
_MAX_TOKEN = 8192
_MAX_DECOMPRESSED_BYTES = 1_000_000
_SCENARIOS = {
    "aprovado",
    "duplicidade",
    "carteirinha_vencida",
    "sem_autorizacao",
    "falha_transitoria",
    "falha_permanente",
}
_GLOSAS = {
    "duplicidade": ("3209", "COBRANÇA DE PROCEDIMENTO/ITEM ASSISTENCIAL EM DUPLICIDADE"),
    "carteirinha_vencida": ("1017", "DATA DE VALIDADE DA CARTEIRA VENCIDA"),
    "sem_autorizacao": ("1818", "COBRANÇA DE PROCEDIMENTO QUE EXIGE AUTORIZAÇÃO PRÉVIA"),
}


class SandboxError(ValueError):
    """Represente uma falha transitória ou permanente da operadora simulada."""

    def __init__(self, codigo: str, mensagem: str, permanente: bool):
        """Registre o código e a permanência da falha."""
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.permanente = permanente


def _local(node: etree._Element) -> str:
    return etree.QName(node).localname if isinstance(node.tag, str) else ""


def _text(node: etree._Element | None, name: str, default: str = "") -> str:
    if node is None:
        return default
    child = next((item for item in node.iter() if _local(item) == name), None)
    return (child.text or "").strip() if child is not None else default


def _first_text(root: etree._Element, name: str, default: str = "") -> str:
    node = next((item for item in root.iter() if _local(item) == name), None)
    return (node.text or "").strip() if node is not None else default


def _money(value: str) -> Decimal:
    try:
        return Decimal(value.replace(",", ".")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Valor monetário inválido: {value!r}") from exc


def _summary(xml: str | bytes) -> dict[str, Any]:
    root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml, parser())
    header = next(node for node in root if _local(node) == "cabecalho")
    origin = next((node for node in header if _local(node) == "origem"), None)
    destination = next((node for node in header if _local(node) == "destino"), None)
    provider = (
        next(
            (
                node
                for node in origin.iter()
                if _local(node) in {"codigoPrestadorNaOperadora", "CNPJ", "CPF"}
            ),
            None,
        )
        if origin is not None
        else None
    )
    provider_type = _local(provider) if provider is not None else "codigoPrestadorNaOperadora"
    provider_value = (provider.text or "").strip() if provider is not None else ""
    registry = _text(destination, "registroANS")
    lot = next(node for node in root.iter() if _local(node) == "loteGuias")
    lot_number = _text(lot, "numeroLote")
    sent_at = _text(header, "dataRegistroTransacao")
    guides_container = next(node for node in lot if _local(node) == "guiasTISS")
    guides: list[dict[str, Any]] = []
    for guide in guides_container:
        guide_number = _text(guide, "numeroGuiaPrestador")
        card = _text(guide, "numeroCarteira")
        items: list[dict[str, Any]] = []
        for item in guide.iter():
            if _local(item) not in {"procedimentoExecutado", "procedimentoRealizado", "despesa"}:
                continue
            procedure = next((node for node in item if _local(node) == "procedimento"), None)
            items.append(
                {
                    "sequencial": _text(item, "sequencialItem"),
                    "data": _text(item, "dataExecucao") or _text(item, "dataRealizacao"),
                    "tabela": _text(procedure, "codigoTabela"),
                    "codigo": _text(procedure, "codigoProcedimento"),
                    "descricao": _text(procedure, "descricaoProcedimento"),
                    "quantidade": _text(item, "quantidadeExecutada") or _text(item, "qtdExecutada"),
                    "valor_total": _text(item, "valorTotal") or _text(item, "valor"),
                }
            )
        if not guide_number:
            raise ValueError("Guia sem numeroGuiaPrestador")
        guides.append(
            {
                "numero_guia_prestador": guide_number,
                "numero_carteira": card,
                "cnes": _text(guide, "CNES"),
                "itens": items,
            }
        )
    return {
        "registro_ans": registry,
        "prestador": {"tipo": provider_type, "valor": provider_value},
        "numero_lote": lot_number,
        "data_envio": sent_at,
        "guias": guides,
    }


def _token(data: dict[str, Any]) -> str:
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    token = _PREFIX + base64.urlsafe_b64encode(zlib.compress(encoded, 9)).decode().rstrip("=")
    if len(token) > _MAX_TOKEN:
        raise ValueError(f"Protocolo excede o limite de {_MAX_TOKEN} caracteres")
    return token


def _decode(protocolo: str) -> dict[str, Any]:
    if (
        not isinstance(protocolo, str)
        or not protocolo.startswith(_PREFIX)
        or len(protocolo) > _MAX_TOKEN
    ):
        raise ValueError("Protocolo inválido")
    raw = protocolo[len(_PREFIX) :]
    try:
        compressed = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
        decoded = zlib.decompressobj().decompress(compressed, _MAX_DECOMPRESSED_BYTES + 1)
        if len(decoded) > _MAX_DECOMPRESSED_BYTES:
            raise ValueError("Protocolo inválido")
        value = json.loads(decoded)
    except (ValueError, zlib.error, json.JSONDecodeError) as exc:
        raise ValueError("Protocolo inválido") from exc
    if not isinstance(value, dict) or set(value) not in (
        {"cenario", "resumo"},
        {"cenario", "resumo", "regras"},
    ):
        raise ValueError("Protocolo inválido")
    if "regras" in value and not isinstance(value["regras"], list):
        raise ValueError("Protocolo inválido")
    return value


def _amount_text(value: Decimal) -> str:
    return f"{value:.2f}"


def _element(parent: etree._Element, name: str, value: Any) -> etree._Element:
    child = etree.SubElement(parent, f"{{{NS}}}{name}")
    child.text = str(value)
    return child


def _provider_tag(provider: dict[str, str]) -> str:
    return (
        provider["tipo"]
        if provider["tipo"] in {"codigoPrestadorNaOperadora", "CNPJ", "CPF"}
        else "codigoPrestadorNaOperadora"
    )


def _provider_name(provider: dict[str, str]) -> str:
    if provider["tipo"] == "CNPJ":
        return "cnpjContratado"
    if provider["tipo"] == "CPF":
        return "cpfContratado"
    return "codigoPrestadorNaOperadora"


def _make_demonstrativo(data: dict[str, Any]) -> bytes:
    summary = data["resumo"]
    scenario = data["cenario"]
    root = etree.Element(f"{{{NS}}}mensagemTISS", nsmap={"ans": NS})
    header = _element(root, "cabecalho", "")
    identification = _element(header, "identificacaoTransacao", "")
    _element(identification, "tipoTransacao", "DEMONSTRATIVO_ANALISE_CONTA")
    _element(identification, "sequencialTransacao", summary["numero_protocolo"])
    _element(identification, "dataRegistroTransacao", summary["data_envio"])
    _element(identification, "horaRegistroTransacao", "12:00:00")
    origin = _element(header, "origem", "")
    _element(origin, "registroANS", summary["registro_ans"])
    destination = _element(header, "destino", "")
    provider_destination = _element(destination, "identificacaoPrestador", "")
    _element(
        provider_destination, _provider_tag(summary["prestador"]), summary["prestador"]["valor"]
    )
    _element(header, "Padrao", "4.03.00")

    healthplan = _element(root, "operadoraParaPrestador", "")
    returns = _element(healthplan, "demonstrativosRetorno", "")
    statement = _element(returns, "demonstrativoAnaliseConta", "")
    statement_header = _element(statement, "cabecalhoDemonstrativo", "")
    _element(statement_header, "registroANS", summary["registro_ans"])
    _element(statement_header, "numeroDemonstrativo", summary["numero_protocolo"])
    _element(statement_header, "nomeOperadora", "Operadora simulada")
    _element(statement_header, "numeroCNPJ", "00000000000000")
    _element(statement_header, "dataEmissao", summary["data_envio"])
    provider = _element(statement, "dadosPrestador", "")
    contracted = _element(provider, "dadosContratado", "")
    _element(contracted, _provider_name(summary["prestador"]), summary["prestador"]["valor"])
    first_guide = next((g for g in summary["guias"] if g["itens"]), None)
    cnes = "0000000"
    if first_guide:
        cnes = first_guide.get("cnes", cnes) or cnes
    _element(provider, "CNES", cnes)

    protocol = _element(statement, "dadosConta", "")
    protocol_data = _element(protocol, "dadosProtocolo", "")
    _element(protocol_data, "numeroLotePrestador", summary["numero_lote"])
    _element(protocol_data, "numeroProtocolo", summary["numero_protocolo"])
    _element(protocol_data, "dataProtocolo", summary["data_envio"])
    _element(protocol_data, "situacaoProtocolo", "3")
    total_informed = Decimal("0.00")
    total_released = Decimal("0.00")
    total_glosa = Decimal("0.00")
    code, description = _GLOSAS.get(scenario, ("", ""))
    rule_findings_by_guide: dict[int, list[dict[str, Any]]] = {}
    for finding in data.get("regras", []):
        pointer = finding.get("pointer", "")
        match = re.fullmatch(r"/guias/(\d+)/dados_autorizacao", pointer)
        if match:
            rule_findings_by_guide.setdefault(int(match.group(1)), []).append(finding)
    for guide_index, guide in enumerate(summary["guias"]):
        relation = _element(protocol_data, "relacaoGuias", "")
        _element(relation, "numeroGuiaPrestador", guide["numero_guia_prestador"])
        _element(relation, "numeroCarteira", guide["numero_carteira"])
        first_date = next(
            (item["data"] for item in guide["itens"] if item.get("data")),
            summary["data_envio"],
        )
        _element(relation, "dataInicioFat", first_date)
        scenario_glosa = scenario in {"duplicidade", "carteirinha_vencida"} or (
            scenario == "sem_autorizacao" and guide_index == 0
        )
        reasons: list[tuple[str, str]] = []
        if scenario_glosa and description:
            reasons.append((code, description))
        for finding in rule_findings_by_guide.get(guide_index, []):
            rule = finding.get("rule") or {}
            rule_code = finding.get("glosa")
            rule_id = rule.get("id")
            if rule_code and rule_id:
                reasons.append((rule_code, f"{finding['message']} (regra {rule_id})"))
        glosar = bool(reasons)
        for reason_code, reason_description in reasons:
            reason = _element(relation, "motivoGlosaGuia", "")
            _element(reason, "codigoGlosa", reason_code)
            _element(reason, "descricaoGlosa", reason_description)
        _element(relation, "situacaoGuia", "4" if glosar else "3")
        guide_informed = Decimal("0.00")
        guide_released = Decimal("0.00")
        guide_glosa = Decimal("0.00")
        for item in guide["itens"]:
            informed = _money(item["valor_total"])
            item_glosa = informed if glosar else Decimal("0.00")
            released = informed - item_glosa
            detail = _element(relation, "detalhesGuia", "")
            _element(detail, "sequencialItem", item["sequencial"])
            _element(detail, "dataRealizacao", item["data"] or summary["data_envio"])
            procedure = _element(detail, "procedimento", "")
            _element(procedure, "codigoTabela", item["tabela"])
            _element(procedure, "codigoProcedimento", item["codigo"])
            _element(procedure, "descricaoProcedimento", item["descricao"])
            _element(detail, "valorInformado", _amount_text(informed))
            _element(detail, "qtdExecutada", item["quantidade"])
            _element(detail, "valorProcessado", _amount_text(informed))
            _element(detail, "valorLiberado", _amount_text(released))
            if item_glosa:
                reason = _element(detail, "relacaoGlosa", "")
                _element(reason, "valorGlosa", _amount_text(item_glosa))
                _element(reason, "tipoGlosa", reasons[0][0])
            guide_informed += informed
            guide_released += released
            guide_glosa += item_glosa
        _element(relation, "valorInformadoGuia", _amount_text(guide_informed))
        _element(relation, "valorProcessadoGuia", _amount_text(guide_informed))
        _element(relation, "valorLiberadoGuia", _amount_text(guide_released))
        _element(relation, "valorGlosaGuia", _amount_text(guide_glosa))
        total_informed += guide_informed
        total_released += guide_released
        total_glosa += guide_glosa
    _element(protocol_data, "valorInformadoProtocolo", _amount_text(total_informed))
    _element(protocol_data, "valorProcessadoProtocolo", _amount_text(total_informed))
    _element(protocol_data, "valorLiberadoProtocolo", _amount_text(total_released))
    _element(protocol_data, "valorGlosaProtocolo", _amount_text(total_glosa))
    _element(statement, "valorInformadoGeral", _amount_text(total_informed))
    _element(statement, "valorProcessadoGeral", _amount_text(total_informed))
    _element(statement, "valorLiberadoGeral", _amount_text(total_released))
    _element(statement, "valorGlosaGeral", _amount_text(total_glosa))
    epilogue_hash = _element(_element(root, "epilogo", ""), "hash", "")
    epilogue_hash.text = hash_epilogo(etree.tostring(root, encoding="UTF-8"))
    return bytes(etree.tostring(root, xml_declaration=True, encoding="UTF-8"))


def enviar_lote(
    xml: str | bytes,
    *,
    cenario: str = "aprovado",
    tentativa: int = 1,
    registro_ans: str | None = None,
) -> dict[str, Any]:
    """Envio e protocolo de lote no cenário escolhido."""
    if cenario not in _SCENARIOS:
        raise ValueError(f"Cenário desconhecido: {cenario}")
    if not isinstance(tentativa, int) or tentativa < 1:
        raise ValueError("tentativa deve ser um inteiro positivo")
    report = validate(xml)
    if not report.valid:
        return {
            "aceito": False,
            "protocolo": None,
            "numero_protocolo": None,
            "numero_lote": _invalid_lot_number(xml),
            "cenario": cenario,
            "findings": [finding.to_dict() for finding in report.findings],
        }
    if cenario == "falha_transitoria" and tentativa == 1:
        raise SandboxError(
            "sandbox.falha_transitoria", "Falha temporária ao receber o lote.", False
        )
    if cenario == "falha_permanente":
        raise SandboxError("sandbox.falha_permanente", "A operadora recusou o lote.", True)
    summary = _summary(xml)
    identity = "|".join(
        [summary["registro_ans"], summary["prestador"]["valor"], summary["numero_lote"]]
    )
    protocol_number = str(int(hashlib.sha256(identity.encode()).hexdigest(), 16) % 10**12).zfill(12)
    package = _package(registro_ans) if registro_ans is not None else None
    findings = (
        rule_findings(dict(parse_lote(xml)), registro_ans)
        if package is not None and registro_ans is not None
        else []
    )
    payload: dict[str, Any] = {
        "cenario": cenario,
        "resumo": {**summary, "numero_protocolo": protocol_number},
    }
    if package is not None:
        payload["regras"] = [finding.to_dict() for finding in findings]
    protocol = _token(payload)
    result = {
        "aceito": True,
        "protocolo": protocol,
        "numero_protocolo": protocol_number,
        "numero_lote": summary["numero_lote"],
        "cenario": cenario,
        "resumo": summary,
        "findings": [],
    }
    if package is not None:
        result["regras"] = [finding.to_dict() for finding in findings]
    return result


def _invalid_lot_number(xml: str | bytes) -> str | None:
    try:
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml, parser())
        return _first_text(root, "numeroLote") or None
    except (etree.XMLSyntaxError, TypeError, ValueError):
        return None


def demonstrativo(protocolo: str) -> bytes:
    """Gere o demonstrativo associado ao protocolo."""
    return _make_demonstrativo(_decode(protocolo))


def responder_autorizacao(
    solicitacao: dict[str, Any] | bytes | str, *, cenario: str = "aprovado"
) -> bytes:
    """Gera resposta SP/SADT sintética no cenário escolhido."""
    if cenario not in {"aprovado", "pendente", "negado"}:
        raise ValueError(f"Cenário desconhecido: {cenario}")
    request = (
        parse_autorizacao(solicitacao) if isinstance(solicitacao, (bytes, str)) else solicitacao
    )
    if not isinstance(request, dict) or "solicitacao" not in request:
        raise ValueError("A mensagem deve conter uma solicitação SP/SADT")
    body = request["solicitacao"]
    identity = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    approved = cenario == "aprovado"
    authorization_data: dict[str, Any] = {
        "numero_guia_prestador": body["cabecalho_solicitacao"]["numero_guia_prestador"],
        "numero_guia_operadora": f"OP{digest[:12]}",
    }
    if approved:
        authorization_data.update(
            {
                "data_autorizacao": body["data_solicitacao"],
                "senha": f"S{digest[12:24]}",
                "data_validade_senha": body["data_solicitacao"],
            }
        )
    procedures = [
        {
            "sequencial_item": str(index),
            "procedimento": item["procedimento"],
            "quantidade_solicitada": item["quantidade_solicitada"],
            "quantidade_autorizada": item["quantidade_solicitada"] if approved else "0",
        }
        for index, item in enumerate(body.get("procedimentos_solicitados", []), start=1)
    ]
    response: dict[str, Any] = {
        "versao": request["versao"],
        "transacao": request["transacao"],
        "prestador": request["prestador"],
        "operadora": request["operadora"],
        "autorizacao": {
            "dados_autorizacao": authorization_data,
            "tipo_etapa_autorizacao": body["tipo_etapa_autorizacao"],
            "dados_beneficiario": body["dados_beneficiario"],
            "nome_beneficiario": "BENEFICIARIO SINTETICO",
            "status_solicitacao": {"aprovado": "1", "pendente": "5", "negado": "3"}[cenario],
            "servicos_autorizados": procedures,
        },
    }
    if cenario == "negado":
        denial_code = "3217"
        if glosa(denial_code) is None:
            raise ValueError("Código de glosa clínica não catalogado")
        response["autorizacao"]["motivos_negativa"] = [denial_code]
        response["autorizacao"]["observacao"] = (
            "Negativa sintética por justificativa clínica ausente ou insuficiente "
            "pela operadora simulada."
        )
    return build_autorizacao(response)


__all__ = [
    "SandboxError",
    "demonstrativo",
    "enviar_lote",
    "responder_autorizacao",
]
