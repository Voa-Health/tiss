"""Exemplos sintéticos em XML."""

from importlib.resources import files

_NAMES = (
    "lote-valido",
    "lote-com-erros",
    "demonstrativo",
    "autorizacao-solicitacao",
    "autorizacao-resposta",
)


def names() -> list[str]:
    """Lista os nomes dos exemplos disponíveis."""
    return list(_NAMES)


def load(name: str) -> bytes:
    """Carrega um exemplo XML pelo nome."""
    if name not in _NAMES:
        raise ValueError(f"Exemplo desconhecido {name!r}; disponíveis: {', '.join(_NAMES)}")
    return (files(__package__) / f"{name}.xml").read_bytes()


__all__ = ["load", "names"]
