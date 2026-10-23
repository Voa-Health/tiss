"""Linha de comando do agente faturista."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from .fluxo import executar, servidor_local
from .modelos import MODELO_PADRAO, criar_modelo

EXEMPLO = Path(__file__).parent / "exemplos" / "atendimentos.csv"


def legivel(resultado: dict[str, Any]) -> str:
    """Formate o resultado estruturado para leitura humana."""
    lote = resultado["lote"]
    linhas = [
        f"Status: {resultado['status']}",
        f"Lote {lote['numero_lote']}: aceito={lote['aceito']} "
        f"protocolo={lote['numero_protocolo']} correções={lote['rodadas_de_correcao']}",
    ]
    for glosa in resultado["glosas"]:
        valor = (
            "valor somado à glosa anterior"
            if glosa["valor_glosa_cents"] is None
            else f"R$ {glosa['valor_glosa_cents'] / 100:.2f}"
        )
        descricao = glosa["descricao"] or "código fora da tabela 38"
        linhas.append(f"Glosa guia {glosa['guia']} {glosa['codigo']} {valor}: {descricao}")
    for recurso in resultado["recursos"]:
        linhas.append(
            f"Recurso guia {recurso['guia']} ({recurso['classe']}): needs="
            f"{','.join(recurso['needs'])} → {recurso['cta']['url']}"
        )
    return "\n".join([*linhas, "", resultado["resumo"]])


def main() -> None:
    """Rode o faturista na linha de comando."""
    parser = argparse.ArgumentParser(prog="faturista")
    parser.add_argument("arquivo", nargs="?", type=Path, default=EXEMPLO)
    parser.add_argument("--modelo", default=os.environ.get("FATURISTA_MODELO", MODELO_PADRAO))
    parser.add_argument("--mcp", default=os.environ.get("TISS_MCP", "local"))
    parser.add_argument("--cenario", default="carteirinha_vencida")
    parser.add_argument("--saida", type=Path, default=Path("resultado.json"))
    args = parser.parse_args()
    modelo = criar_modelo(args.modelo, cenario=args.cenario)
    servidor = servidor_local() if args.mcp == "local" else nullcontext(args.mcp)

    def relatar(texto: str) -> None:
        sys.stderr.write(texto + "\n")

    with servidor as url:
        resultado = asyncio.run(
            executar(args.arquivo, modelo, url=url, cenario=args.cenario, relatar=relatar)
        )
    args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n")
    sys.stdout.write(f"{legivel(resultado)}\n\nJSON: {args.saida}\n")
    sys.exit(0 if resultado["status"] == "concluido" else 1)


if __name__ == "__main__":
    main()
