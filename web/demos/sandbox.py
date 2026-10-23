from tiss import examples, parse_demonstrativo
from tiss.sandbox import demonstrativo, enviar_lote

lote = examples.load("lote-valido")
resposta = enviar_lote(lote, registro_ans="000000")
print("aceito:", resposta["aceito"], resposta["numero_protocolo"])
for achado in resposta["regras"]:
    print("regra:", achado["rule"]["id"], achado["code"])

for decisao in parse_demonstrativo(demonstrativo(resposta["protocolo"])):
    glosa = f"R$ {decisao.valor_glosa_cents / 100:.2f}"
    motivo = decisao.motivo.split(" (")[0]
    print(decisao.guia_ref, decisao.decision, glosa, motivo)
