import json
from pathlib import Path

from voa_tiss import check, examples, parse_lote
from voa_tiss._rules import validate_package

pacote = json.loads(Path("pacote-operadora.json").read_text())
print("pacote:", validate_package(pacote) or "válido")
comunidade = {**pacote, "mantenedor": {"tipo": "comunidade"}}
print("comunidade:", *validate_package(comunidade))

lote = parse_lote(examples.load("lote-valido"))
achado = next(a for a in check(lote, operadora=pacote).findings if a.rule)
print(achado.rule["id"], "oficial:", achado.rule["source"]["official"])
