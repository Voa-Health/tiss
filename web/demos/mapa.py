from voa_tiss import examples, parse_lote, rejection_map

lotes = [parse_lote(examples.load("lote-valido")) for _ in range(2)]
lotes[0]["prestador"] = {"cnpj": "11222333000181"}
lotes[0]["guias"][0]["procedimentos_executados"][0]["valor_total"] = 0
lotes[1]["prestador"] = {"cpf": "123.456.789-09"}
mapa = rejection_map(lotes, operadora="000000", segredo_pseudonimo="s" * 16)
for linha in mapa["linhas"]:
    prestador, valor = linha["prestador"][:22], linha["valor_afetado"]
    print(f"{prestador:23} {linha['codigo']:24} {linha['guias']} R$ {valor}")
