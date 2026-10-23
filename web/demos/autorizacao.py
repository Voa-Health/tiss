from tiss import check_autorizacao, examples, parse_autorizacao

solicitacao = parse_autorizacao(examples.load("autorizacao-solicitacao"))
relatorio = check_autorizacao(solicitacao, contexto={"operadora": "000000"})

print("decisão:", relatorio.decisao["tipo"])
for regra in relatorio.decisao["rules"]:
    print("regra:", regra["id"], regra["source"]["url"])
for achado in relatorio.findings:
    print(achado.severity, achado.code)
