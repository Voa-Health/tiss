from __future__ import annotations

import datetime as dt
import json
import logging
from functools import cache
from typing import Any

import jsonschema

import tiss
from tiss import operadoras, sandbox
from tiss import rede as _rede_module
from tiss._retorno import Decisao, RetornoError
from tiss.rede import RedeIndisponivel
from tiss.sandbox import SandboxError
from tiss.tuss import lookup, search

from ._context import CallContext
from ._docs import _load_readme, search_docs
from ._docs import render_api_docs as _render_api_docs
from ._mcp_data import RESOURCE_DEFINITIONS, RESOURCE_TEMPLATE_DEFINITIONS
from ._ops_autorizacao import AUTORIZACAO_OPS
from ._ops_consulta import CONSULTA_OPS
from ._ops_lote import LOTE_OPS
from ._ops_schemas import (
    _ESTABELECIMENTO_ITEM,
    _LIMIT,
    _LOTE_OBJECT_SCHEMA,
    _REDE_ITEM,
    _STRING_ITEMS,
    Op,
    _array,
    _object,
    _string,
)
from ._prompts import PROMPTS
from ._published_rules import with_published_rules
from ._quota import admit, payment_required
from ._telemetry import operation_event
from ._usage import API_CALL, record, wait

logger = logging.getLogger("tiss.server")
_USAGE_WAIT_SECONDS = 2.0
_HTTP_OK = 200


def _decision(value: dict[str, Any]) -> Decisao:
    return Decisao(**value)


def _parse(value: dict[str, Any]) -> dict[str, Any]:
    return {"decisoes": [decision.to_dict() for decision in tiss.parse_demonstrativo(value["xml"])]}


def _reconcile(value: dict[str, Any]) -> dict[str, Any]:
    decisions = [_decision(item) for item in value["decisoes"]]
    result = tiss.plan_reconciliation(
        decisions,
        value["guias"],
        id_key=value.get("id_key", "id"),
        prestador_key=value.get("prestador_key", "numero_guia_prestador"),
        operadora_key=value.get("operadora_key", "numero_guia_operadora"),
        status_key=value.get("status_key", "status"),
    )
    return {
        "propostas": [
            {
                "guia": proposal.guia,
                "acao": proposal.acao,
                "motivo": proposal.motivo,
                "decisoes": [item.to_dict() for item in proposal.decisoes],
            }
            for proposal in result.propostas
        ],
        "sem_par": [item.to_dict() for item in result.sem_par],
        "ambiguas": [item.to_dict() for item in result.ambiguas],
    }


def _date(value: dict[str, Any]) -> dt.date | None:
    raw = value.get("data")
    return dt.date.fromisoformat(raw) if raw else None


def _lookup(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "resultados": lookup(
            value["code"],
            tabela=value.get("tabela"),
            include_expired=value.get("include_expired", True),
            today=_date(value),
        )
    }


def _search(value: dict[str, Any]) -> dict[str, Any]:
    limit = value.get("limite", 20)
    return {
        "resultados": search(
            value["text"],
            tabela=value.get("tabela"),
            include_expired=value.get("include_expired", False),
            today=_date(value),
        )[:limit]
    }


def _healthplan_profile(value: dict[str, Any]) -> dict[str, Any]:
    result = operadoras.perfil(value["registro_ans"])
    if result is None:
        raise LookupError(f"Operadora não encontrada: {value['registro_ans']}")
    return result


def _sandbox_send(value: dict[str, Any]) -> dict[str, Any]:
    return sandbox.enviar_lote(
        value["xml"],
        cenario=value.get("cenario", "aprovado"),
        tentativa=value.get("tentativa", 1),
        registro_ans=value.get("registro_ans"),
    )


def _sandbox_statement(value: dict[str, Any]) -> dict[str, Any]:
    xml = sandbox.demonstrativo(value["protocolo"])
    return {"protocolo": value["protocolo"], "xml": xml.decode("utf-8")}


def _rede_lookup(value: dict[str, Any]) -> dict[str, Any]:
    if ("cnpj" in value) == ("cnes" in value):
        raise ValueError("Informe exatamente um dos campos 'cnpj' ou 'cnes'.")
    limite = value.get("limite", 200)
    operadoras = _rede_module.operadoras_do_estabelecimento(
        cnpj=value.get("cnpj"), cnes=value.get("cnes")
    )
    return {
        "atualizado_em": _rede_module.atualizado_em(),
        "fonte": _rede_module.fonte(),
        "total": len(operadoras),
        "operadoras": operadoras[:limite],
    }


def _operadora_rede(value: dict[str, Any]) -> dict[str, Any]:
    limite = value.get("limite", 200)
    resumo = _rede_module.resumo_da_operadora(value["registro"])
    estabelecimentos = _rede_module.estabelecimentos_da_operadora(
        resumo["registro_ans"], uf=value.get("uf")
    )
    return {
        "atualizado_em": _rede_module.atualizado_em(),
        "fonte": _rede_module.fonte(),
        "registro_ans": resumo["registro_ans"],
        "total": resumo["estabelecimentos"],
        "por_uf": resumo["por_uf"],
        "estabelecimentos": estabelecimentos[:limite],
    }


_DECISION_SCHEMA = _object(
    {
        "guia_ref": _string(),
        "decision": {"enum": ["pago", "glosado", "glosa_parcial"]},
        "motivo": _string(),
        "guia_operadora": _string(),
        "tuss_code": _string(),
        "valor_glosa_cents": {"type": "integer"},
        "valor_liberado_cents": {"type": "integer"},
    },
    ["guia_ref", "decision", "motivo"],
    additional=True,
)
_RESULTS = _object({"resultados": _array(_object({}, additional=True))}, ["resultados"])
_DECISIONS = _object({"decisoes": _array(_DECISION_SCHEMA)}, ["decisoes"])
_RECONCILIATION = _object(
    {
        "propostas": _array(_object({}, additional=True)),
        "sem_par": _array(_DECISION_SCHEMA),
        "ambiguas": _array(_DECISION_SCHEMA),
    },
    ["propostas", "sem_par", "ambiguas"],
)
_REPORT = tiss.json_schema("report")
_SANDBOX_SEND = _object(
    {
        "aceito": {"type": "boolean"},
        "protocolo": {"type": ["string", "null"]},
        "numero_protocolo": {"type": ["string", "null"]},
        "numero_lote": {"type": ["string", "null"]},
        "cenario": _string(),
        "resumo": _object({}, additional=True),
        "findings": _array(_object({}, additional=True)),
    },
    ["aceito", "protocolo", "numero_protocolo", "numero_lote", "cenario", "findings"],
    additional=True,
)
_XML_INPUT = _object({"xml": _string()}, ["xml"])
_EMPTY = _object({})
_AUDIT_CONTEXT_SCHEMA = {
    key: value
    for key, value in tiss.json_schema("audit_context").items()
    if key not in {"$schema", "title"}
}
_VALIDATE_INPUT = _object(
    {
        "xml": _string(),
        "lote": _LOTE_OBJECT_SCHEMA,
        "operadora": {"type": "string", "pattern": "^[0-9]{5,6}$"},
        "contexto": _AUDIT_CONTEXT_SCHEMA,
        "data": {"type": "string", "format": "date"},
    }
)


def _validate(value: dict[str, Any]) -> dict[str, Any]:
    if ("xml" in value) == ("lote" in value):
        raise ValueError("Informe exatamente um dos campos 'xml' ou 'lote'.")
    if "xml" in value:
        return tiss.validate(value["xml"], operadora=value.get("operadora")).to_dict()
    return tiss.check(
        value["lote"],
        contexto=value.get("contexto"),
        operadora=value.get("operadora"),
        at=value.get("data"),
    ).to_dict()


def _buscar_docs(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "resultados": search_docs(
            _docs_corpus(),
            value["texto"],
            value.get("limite", 3),
        )
    }


buscar_docs_op = Op(
    "buscar_docs",
    _buscar_docs,
    _object(
        {
            "texto": _string(),
            "limite": {"type": "integer", "minimum": 1, "maximum": 10, "default": 3},
        },
        ["texto"],
    ),
    _object(
        {
            "resultados": _array(
                _object(
                    {"uri": _string(), "titulo": _string(), "trecho": _string()},
                    ["uri", "titulo", "trecho"],
                )
            )
        },
        ["resultados"],
    ),
    (
        "Busca trechos da documentação local da biblioteca. "
        "Quando usar: para encontrar instruções e referências da API. "
        "Quando não usar: para consultar dados clínicos ou códigos específicos."
    ),
    2000,
    method="GET",
    path="/v1/docs",
)

_BASE_OPS = (
    Op(
        "validate",
        _validate,
        _VALIDATE_INPUT,
        _REPORT,
        (
            "Valida XML TISS ou lote em JSON. Quando usar: antes de gerar ou enviar um lote. "
            "Quando não usar: para corrigir achados sem aplicar o ciclo "
            "validar → tiss_apply_fixes → validar de novo."
        ),
        2500,
        scope="tiss:validate",
        rules_input="operadora",
    ),
    Op(
        "parse_demonstrativo",
        _parse,
        _XML_INPUT,
        _DECISIONS,
        (
            "Lê decisões de um demonstrativo. Quando usar: para identificar pagamentos e glosas. "
            "Quando não usar: para validar lotes."
        ),
        1800,
        scope="tiss:accounts",
    ),
    Op(
        "plan_reconciliation",
        _reconcile,
        _object(
            {
                "decisoes": _array(_DECISION_SCHEMA),
                "guias": _array(_object({}, additional=True)),
                "id_key": _string(),
                "prestador_key": _string(),
                "operadora_key": _string(),
                "status_key": _string(),
            },
            ["decisoes", "guias"],
        ),
        _RECONCILIATION,
        (
            "Propõe vínculos entre decisões e guias. Quando usar: após ler um demonstrativo. "
            "Quando não usar: para alterar guias."
        ),
        3000,
        scope="tiss:accounts",
    ),
    Op(
        "tuss_lookup",
        _lookup,
        _object(
            {
                "code": _string(),
                "tabela": _string(),
                "include_expired": {"type": "boolean"},
                "data": {"type": "string", "format": "date"},
            },
            ["code"],
        ),
        _RESULTS,
        (
            "Busca um código TUSS exato. Quando usar: para consultar código ou vigência. "
            "Quando não usar: para buscar por descrição."
        ),
        5000,
    ),
    Op(
        "tuss_search",
        _search,
        _object(
            {
                "text": _string(),
                "tabela": _string(),
                "include_expired": {"type": "boolean"},
                "data": {"type": "string", "format": "date"},
                "limite": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            },
            ["text"],
        ),
        _RESULTS,
        (
            "Busca códigos TUSS por texto. Quando usar: para localizar "
            "procedimentos por descrição. Quando não usar: para validar XML."
        ),
        6000,
    ),
    Op(
        "sadt_missing",
        lambda value: {"faltando": tiss.sadt_missing(value["values"])},
        _object({"values": _object({}, additional=True)}, ["values"]),
        _object({"faltando": _STRING_ITEMS}, ["faltando"]),
        (
            "Identifica campos obrigatórios SP/SADT ausentes. Quando usar: antes de "
            "renderizar uma guia. Quando não usar: para validar um lote."
        ),
        1000,
        scope="tiss:validate",
    ),
    Op(
        "sadt_catalog",
        lambda value: tiss.sadt_catalog(),
        _EMPTY,
        _object({}, additional=True),
        (
            "Retorna o catálogo SP/SADT. Quando usar: para conhecer campos e domínios. "
            "Quando não usar: para preencher uma guia sem dados."
        ),
        10000,
        scope="tiss:validate",
    ),
    Op(
        "rede",
        _rede_lookup,
        _object({"cnpj": _string(), "cnes": _string(), "limite": _LIMIT}),
        _object(
            {
                "atualizado_em": _string(),
                "fonte": _string(),
                "total": {"type": "integer"},
                "operadoras": _array(_REDE_ITEM),
            },
            ["atualizado_em", "fonte", "total", "operadoras"],
        ),
        (
            "Consulta as operadoras vinculadas a um CNPJ ou CNES. "
            "Quando usar: para identificar vínculos de um estabelecimento. "
            "Quando não usar: para buscar o cadastro geral; use operadora_lookup."
        ),
        20000,
        method="GET",
        path="/v1/rede",
    ),
    Op(
        "operadora_rede",
        _operadora_rede,
        _object(
            {
                "registro": _string(),
                "uf": {"type": "string", "pattern": "^[A-Za-z]{2}$"},
                "limite": _LIMIT,
            },
            ["registro"],
        ),
        _object(
            {
                "atualizado_em": _string(),
                "fonte": _string(),
                "registro_ans": _string(),
                "total": {"type": "integer"},
                "por_uf": {"type": "object", "additionalProperties": {"type": "integer"}},
                "estabelecimentos": _array(_ESTABELECIMENTO_ITEM),
            },
            [
                "atualizado_em",
                "fonte",
                "registro_ans",
                "total",
                "por_uf",
                "estabelecimentos",
            ],
        ),
        (
            "Consulta os estabelecimentos vinculados a uma operadora. "
            "Quando usar: para identificar unidades da rede por UF. "
            "Quando não usar: para buscar o cadastro geral; use operadora_lookup."
        ),
        20000,
        method="GET",
        path="/v1/operadoras/{registro}/rede",
    ),
    Op(
        "operadora_perfil",
        _healthplan_profile,
        _object({"registro_ans": {"type": "string", "pattern": "^[0-9]{5,6}$"}}, ["registro_ans"]),
        _object(
            {
                "registro_ans": _string(),
                "razao_social": _string(),
                "indicadores": _object(
                    {
                        "fonte": _object({}, additional=True),
                        "serie": _array(_object({}, additional=True)),
                    },
                    ["fonte", "serie"],
                ),
            },
            ["registro_ans", "razao_social", "indicadores"],
            additional=True,
        ),
        (
            "Consulta o cadastro e a série semestral de glosa e pagamento de uma operadora na ANS. "
            "Quando usar: para conhecer uma operadora pelo registro ANS. "
            "Quando não usar: para buscar operadoras por nome."
        ),
        2500,
        method="GET",
        path="/v1/operadoras/{registro_ans}",
    ),
    Op(
        "sandbox_enviar_lote",
        _sandbox_send,
        _object(
            {
                "xml": _string(),
                "cenario": {
                    "enum": [
                        "aprovado",
                        "duplicidade",
                        "carteirinha_vencida",
                        "sem_autorizacao",
                        "falha_transitoria",
                        "falha_permanente",
                    ]
                },
                "tentativa": {"type": "integer", "minimum": 1},
                "registro_ans": {"type": "string", "pattern": "^[0-9]{5,6}$"},
            },
            ["xml"],
        ),
        _SANDBOX_SEND,
        (
            "Envia um lote à operadora simulada. Quando usar: para testar integração local. "
            "Quando não usar: para transmitir dados reais."
        ),
        2500,
        path="/v1/sandbox/lotes",
        scope="tiss:sandbox",
        rules_input="registro_ans",
    ),
    Op(
        "sandbox_demonstrativo",
        _sandbox_statement,
        _object({"protocolo": _string()}, ["protocolo"]),
        _object({"protocolo": _string(), "xml": _string()}, ["protocolo", "xml"]),
        (
            "Gera o demonstrativo de um protocolo simulado. Quando usar: após enviar um lote. "
            "Quando não usar: com protocolo de outra operadora."
        ),
        5000,
        method="GET",
        path="/v1/sandbox/lotes/{protocolo}/demonstrativo",
        scope="tiss:sandbox",
    ),
)
OPS = (*_BASE_OPS, *LOTE_OPS, *CONSULTA_OPS, *AUTORIZACAO_OPS, buscar_docs_op)

_VALIDATORS = {
    op.name: jsonschema.Draft202012Validator(
        op.input_schema, format_checker=jsonschema.FormatChecker()
    )
    for op in OPS
}


def call(
    op: Op, entrada: dict[str, Any], ctx: CallContext | None = None
) -> tuple[int, dict[str, Any]]:
    ctx = ctx or CallContext()
    denied = admit(op.name, ctx, op.scope) or payment_required(op, ctx.access)
    if denied is not None:
        logger.info("op=%s status=%d ms=0.0", op.name, denied[0])
        return denied
    started = dt.datetime.now(dt.timezone.utc)
    status = _HTTP_OK
    try:
        _VALIDATORS[op.name].validate(entrada)
        result = op.run(with_published_rules(op, entrada, ctx))
    except jsonschema.ValidationError as exc:
        status = 422
        result = {"erro": {"codigo": "entrada_invalida", "mensagem": exc.message}}
    except SandboxError as exc:
        status = 422 if exc.permanente else 503
        result = {
            "erro": {
                "codigo": exc.codigo,
                "mensagem": exc.mensagem,
                "permanente": exc.permanente,
            }
        }
    except RedeIndisponivel as exc:
        status = 503
        result = {"erro": {"codigo": "rede_indisponivel", "mensagem": str(exc)}}
    except LookupError as exc:
        status = 404
        result = {"erro": {"codigo": "nao_encontrado", "mensagem": str(exc.args[0])}}
    except (RetornoError, ValueError, TypeError) as exc:
        status = 422
        result = {"erro": {"codigo": "entrada_invalida", "mensagem": str(exc)}}
    elapsed = (dt.datetime.now(dt.timezone.utc) - started).total_seconds() * 1000
    logger.info("op=%s status=%d ms=%.1f", op.name, status, elapsed)
    if ctx.access is not None:
        record(ctx.access, op.name, op.usage_kind if status == _HTTP_OK else API_CALL, started)
        if ctx.background_tasks is not None:
            ctx.background_tasks.add_task(wait, _USAGE_WAIT_SECONDS)
    operation_event(
        op.name,
        entrada,
        result,
        telemetry_off=ctx.telemetry_off,
        background_tasks=ctx.background_tasks,
    )
    return status, result


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def token_estimate(value: Any) -> int:
    return (len(json_bytes(value)) + 3) // 4


def render_api_docs() -> str:
    return _render_api_docs(
        OPS,
        PROMPTS,
        RESOURCE_DEFINITIONS,
        RESOURCE_TEMPLATE_DEFINITIONS,
    )


@cache
def _docs_corpus() -> dict[str, str]:
    return {
        "tiss://docs/readme": _load_readme(),
        "tiss://docs/api": render_api_docs(),
    }
