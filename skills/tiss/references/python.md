# Python

Instale a biblioteca com `pip install tiss`. O exemplo usa um lote TISS
sintético do pacote, introduz um valor divergente, aplica a correção e gera XML.

```python
from tiss import apply_fixes, build_lote, check, examples, hash_epilogo, parse_lote

lote = parse_lote(examples.load("lote-valido"))
item = lote["guias"][0]["procedimentos_executados"][0]
item["valor_total"] += 1

for _ in range(3):
    relatorio = check(lote)
    erros = [achado for achado in relatorio.findings if achado.severity == "error"]
    if not erros:
        break
    pendencias = [achado for achado in erros if achado.needs]
    if pendencias:
        campos = sorted({campo for achado in pendencias for campo in achado.needs})
        raise ValueError(f"Peça ao usuário somente estes dados: {campos}")
    corrigido = apply_fixes(lote, relatorio)
    if corrigido == lote:
        break
    lote = corrigido

relatorio = check(lote)
if not relatorio.valid:
    raise ValueError("O lote ainda tem erros; revise os achados.")

xml = build_lote(lote)
hash_xml = hash_epilogo(xml)
print({"bytes_xml": len(xml), "hash_epilogo": hash_xml})
```

Para ler demonstrativos, use `parse_demonstrativo`; consulte TUSS em
`tiss.tuss` e glosas com `tiss.glosa`. A operadora simulada fica em
`tiss.sandbox`.
