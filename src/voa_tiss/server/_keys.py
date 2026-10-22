from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any

KEY_TTL_SECONDS = 86_400
ANONYMOUS_LIMIT = 10
TIER_LIMITS = {"login": 50, "verified": 1_000}
SITE_URL = "https://tiss-api.voa.health"
LOGIN_URL = f"{SITE_URL}/chaves"
ENTERPRISE_URL = "https://voa.health"
LIMITS = {
    "limite_diario": None,
    "sem_chave": {"operacoes": ["sandbox_*", "lista_de_espera"], "login": LOGIN_URL},
    "niveis": sorted(TIER_LIMITS),
    "chave_invalida": {"status": 401},
    "validade_chave_segundos": KEY_TTL_SECONDS,
}


class KeyConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Access:
    org: str
    tier: str


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _secret() -> bytes:
    secret = os.environ.get("VOA_TISS_KEY_SECRET")
    if not secret:
        raise KeyConfigurationError("Emissão de chaves indisponível.")
    return secret.encode()


def _mac(kind: str, payload: str) -> str:
    return _b64(hmac.new(_secret(), f"{kind}.{payload}".encode(), hashlib.sha256).digest())


def sign(kind: str, data: dict[str, Any]) -> str:
    payload = _b64(json.dumps(data, separators=(",", ":")).encode())
    return f"{payload}.{_mac(kind, payload)}"


def unsign(kind: str, token: str | None) -> dict[str, Any] | None:
    """Devolva os dados assinados e ainda válidos, ou `None`."""
    try:
        payload, signature = (token or "").split(".", 1)
        if not hmac.compare_digest(signature, _mac(kind, payload)):
            return None
        data: Any = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (KeyConfigurationError, ValueError, TypeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("e"), int):
        return None
    return data if data["e"] > time.time() else None


def issue_key(org: str, tier: str) -> tuple[str, int]:
    expires = int(time.time()) + KEY_TTL_SECONDS
    return f"vt_{sign('key', {'o': org, 'n': tier, 'e': expires})}", expires


def read_key(value: str) -> Access | None:
    data = unsign("key", value[3:]) if value.startswith("vt_") else None
    if data is None or set(data) != {"o", "n", "e"} or data["n"] not in TIER_LIMITS:
        return None
    return Access(org=str(data["o"]), tier=data["n"])


def authorize(header: str | None) -> tuple[bool, Access | None]:
    """Separe pedido sem chave, chave válida e chave inválida ou expirada."""
    if header is None:
        return True, None
    prefix, _, value = header.partition(" ")
    access = read_key(value) if prefix.lower() == "bearer" else None
    return access is not None, access


__all__ = [
    "ANONYMOUS_LIMIT",
    "ENTERPRISE_URL",
    "LIMITS",
    "LOGIN_URL",
    "SITE_URL",
    "TIER_LIMITS",
    "Access",
    "KeyConfigurationError",
    "authorize",
    "issue_key",
    "read_key",
    "sign",
    "unsign",
]
