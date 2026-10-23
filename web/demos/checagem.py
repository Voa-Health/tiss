import json
from pathlib import Path

from tiss import check, examples, parse_lote

lote = parse_lote(examples.load("lote-valido"))
pacote = json.loads(Path("pacote-operadora.json").read_text())
for achado in check(lote, operadora=pacote).findings:
    if achado.rule:
        print(achado.severity, achado.rule["id"], achado.pointer)
        print("  ", achado.message)
        print("   fonte:", achado.rule["source"]["url"])
