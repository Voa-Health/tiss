from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


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
        return (
            self.name
            if self.name.startswith(("tuss_", "operadora_", "glosa_", "buscar_"))
            else f"tiss_{self.name}"
        )


def _object(
    properties: dict[str, Any],
    required: list[str] | None = None,
    *,
    additional: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": additional,
    }
    if required:
        result["required"] = required
    return result


def _array(item: dict[str, Any]) -> dict[str, Any]:
    return {"type": "array", "items": item}


def _string() -> dict[str, Any]:
    return {"type": "string"}


_LOTE_OBJECT_SCHEMA = _object({}, additional=True)
_LOTE_OBJECT_SCHEMA["description"] = "Schema estrutural disponível em tiss://schemas/lote."


_STRING_ITEMS = _array(_string())
_LIMIT = {"type": "integer", "minimum": 1, "maximum": 1000, "default": 200}
_REDE_ITEM = _object(
    {
        "registro_ans": _string(),
        "nome": {"type": ["string", "null"]},
        "cnes": {"type": ["string", "null"]},
        "nome_estabelecimento": _string(),
        "tipo_contrato": _STRING_ITEMS,
        "disponibilidade": _STRING_ITEMS,
        "tipo_prestador": _STRING_ITEMS,
        "urgencia_emergencia": {"type": "boolean"},
        "dt_vinculo_inicio": {"type": ["string", "null"]},
        "planos": {"type": "integer"},
    },
    [
        "registro_ans",
        "nome",
        "cnes",
        "nome_estabelecimento",
        "tipo_contrato",
        "disponibilidade",
        "tipo_prestador",
        "urgencia_emergencia",
        "dt_vinculo_inicio",
        "planos",
    ],
)
_ESTABELECIMENTO_ITEM = _object(
    {
        "cnes": {"type": ["string", "null"]},
        "cnpj": {"type": ["string", "null"]},
        "nome": _string(),
        "classe": {"type": ["string", "null"]},
        "cd_municipio": {"type": ["string", "null"]},
        "uf": _string(),
        "tipo_contrato": _STRING_ITEMS,
        "disponibilidade": _STRING_ITEMS,
        "tipo_prestador": _STRING_ITEMS,
        "urgencia_emergencia": {"type": "boolean"},
        "dt_vinculo_inicio": {"type": ["string", "null"]},
        "planos": {"type": "integer"},
    },
    [
        "cnes",
        "cnpj",
        "nome",
        "classe",
        "cd_municipio",
        "uf",
        "tipo_contrato",
        "disponibilidade",
        "tipo_prestador",
        "urgencia_emergencia",
        "dt_vinculo_inicio",
        "planos",
    ],
)
