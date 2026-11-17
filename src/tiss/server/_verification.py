from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response

OPENAI_DOMAIN_CHALLENGE = "xYqs1EKAzE2JZx4ugObYkpi3vkRByO8SgrMWHzoSj1c"


def openai_domain_challenge(_: Request) -> Response:
    return Response(OPENAI_DOMAIN_CHALLENGE, media_type="text/plain")
