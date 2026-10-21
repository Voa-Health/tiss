from __future__ import annotations

import datetime as dt
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import jsonschema

import voa_tiss
from voa_tiss import operadoras, sandbox
from voa_tiss import rede as _rede_module
from voa_tiss._retorno import Decisao, RetornoError
from voa_tiss.rede import RedeIndisponivel
from voa_tiss.sandbox import SandboxError
from voa_tiss.tuss import lookup, search

from ._context import CallContext
from ._keys import KEY_TTL_SECONDS
from ._ops_schemas import (
    _ESTABELECIMENTO_ITEM,
    _LIMIT,
    _REDE_ITEM,
    _STRING_ITEMS,
    _array,
    _object,
    _string,
)
from ._quota import admit
from ._telemetry import operation_event

logger = logging.getLogger("voa_tiss.server")


@dataclass(frozen=True)
class Op:
    name: str
    run: Callable[[dict[str, Any]], dict[str, Any]]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    description: str
    max_tokens: int
    method: str = "POST"
    path: str | None = None

    @property
    def route(self) -> str:
        return self.path or f"/v1/{self.name}"

    @property
    def tool_name(self) -> str:
        return self.name if self.name.startswith(("tuss_", "operadora_")) else f"tiss_{self.name}"


def _decision(value: dict[str, Any]) -> Decisao:
    return Decisao(**value)


def _parse(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "decisoes": [decision.to_dict() for decision in voa_tiss.parse_demonstrativo(value["xml"])]
    }


def _reconcile(value: dict[str, Any]) -> dict[str, Any]:
    decisions = [_decision(item) for item in value["decisoes"]]
    result = voa_tiss.plan_reconciliation(
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


def _operator_profile(value: dict[str, Any]) -> dict[str, Any]:
    result = operadoras.perfil(value["registro_ans"])
    if result is None:
        raise LookupError(f"Operadora não encontrada: {value['registro_ans']}")
    return result


def _sandbox_send(value: dict[str, Any]) -> dict[str, Any]:
    return sandbox.enviar_lote(
        value["xml"],
        cenario=value.get("cenario", "aprovado"),
        tentativa=value.get("tentativa", 1),
    )


def _sandbox_statement(value: dict[str, Any]) -> dict[str, Any]:
    xml = sandbox.demonstrativo(value["protocolo"])
    return {"protocolo": value["protocolo"], "xml": xml.decode("utf-8")}


def _rede_lookup(value: dict[str, Any]) -> dict[str, Any]:
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
_REPORT = voa_tiss.json_schema("report")
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

OPS = (
    Op(
        "validate",
        lambda value: voa_tiss.validate(value["xml"]).to_dict(),
        _XML_INPUT,
        _REPORT,
        (
            "Valida um XML TISS. Quando usar: antes de enviar um lote. "
            "Quando não usar: para interpretar glosas."
        ),
        2500,
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
        lambda value: {"faltando": voa_tiss.sadt_missing(value["values"])},
        _object({"values": _object({}, additional=True)}, ["values"]),
        _object({"faltando": _STRING_ITEMS}, ["faltando"]),
        (
            "Identifica campos obrigatórios SP/SADT ausentes. Quando usar: antes de "
            "renderizar uma guia. Quando não usar: para validar um lote."
        ),
        1000,
    ),
    Op(
        "sadt_catalog",
        lambda value: voa_tiss.sadt_catalog(),
        _EMPTY,
        _object({}, additional=True),
        (
            "Retorna o catálogo SP/SADT. Quando usar: para conhecer campos e domínios. "
            "Quando não usar: para preencher uma guia sem dados."
        ),
        10000,
    ),
    Op(
        "rede",
        _rede_lookup,
        {
            **_object({"cnpj": _string(), "cnes": _string(), "limite": _LIMIT}),
            "oneOf": [
                {"required": ["cnpj"], "not": {"required": ["cnes"]}},
                {"required": ["cnes"], "not": {"required": ["cnpj"]}},
            ],
        },
        _object(
            {
                "atualizado_em": _string(),
                "fonte": _string(),
                "total": {"type": "integer"},
                "operadoras": _array(_REDE_ITEM),
            },
            ["atualizado_em", "fonte", "total", "operadoras"],
        ),
        "Consulta as operadoras vinculadas a um CNPJ ou CNES.",
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
        "Consulta os estabelecimentos vinculados a uma operadora.",
        20000,
        method="GET",
        path="/v1/operadoras/{registro}/rede",
    ),
    Op(
        "operadora_perfil",
        _operator_profile,
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
    ),
)

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
    denied = admit(op.name, ctx)
    if denied is not None:
        logger.info("op=%s status=%d ms=0.0", op.name, denied[0])
        return denied
    started = dt.datetime.now(dt.timezone.utc)
    status = 200
    try:
        _VALIDATORS[op.name].validate(entrada)
        result = op.run(entrada)
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


def _escape_markdown(value: str) -> str:
    return value.replace("|", "\\|")


def render_api_docs() -> str:
    rows = """# API HTTP e MCP

Orçamento aproximado: `ceil(tamanho UTF-8 do JSON / 4)` tokens.

| Operação | Rota HTTP | Tool MCP | Descrição | Orçamento |
| --- | --- | --- | --- | ---: |""".splitlines()
    rows.extend(
        f"| `{op.name}` | `{op.method} {op.route}` | `{op.tool_name}` | "
        f"{_escape_markdown(op.description)} | {op.max_tokens} |"
        for op in OPS
    )
    rows.extend(
        [
            "",
            "## Acesso",
            "",
            "Sem chave, só as operações `sandbox_*` respondem. As demais exigem a chave",
            "do login Voa em `Authorization: Bearer`. Não há limite diário.",
            "Chave inválida ou expirada retorna `401`.",
            f"A chave vale {KEY_TTL_SECONDS // 3600} h e é renovada com o `refresh_token`.",
            "",
            "| Rota HTTP | Descrição |",
            "| --- | --- |",
            "| `GET /v1/auth/login` | Inicia o login Voa. |",
            "| `GET /v1/auth/callback` | Emite a chave e volta para `/chaves`. |",
            "| `POST /v1/keys/refresh` | Troca o `refresh_token` por uma chave nova. |",
            "| `GET /v1/limits` | Regras de acesso. |",
            "| `GET /oauth/client.json` | Metadados do cliente OAuth. |",
        ]
    )
    return "\n".join(rows) + "\n"
