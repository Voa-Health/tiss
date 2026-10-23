# Registro de alterações

## Não lançado

- A API hospedada aceita chaves `sk_tiss_` da organização, com escopo por operação,
  revogação em até 60 segundos e uso registrado por chamada.
- TISS-Bench: 40 tarefas sintéticas com verificação determinística e resultados
  de quatro modelos com e sem o MCP.
- Ferramentas MCP passam a usar esquemas de entrada com objeto no topo, compatíveis
  com clientes como Claude.
- Guias de consulta geradas por `build_lote` seguem a ordem definida pelo XSD.
- A validação identifica divergências no hash do epílogo.
