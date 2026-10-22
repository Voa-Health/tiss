# TISS-Bench

Benchmark público e reproduzível de tarefas sintéticas TISS 4.03.00 para comparar
agentes de código com e sem as ferramentas MCP do `voa-tiss`.

## Tarefas

São 40 tarefas determinísticas:

| Categoria | Profissional | Prestador | Operadora | Gestor | Paciente | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Geração | 2 | 6 | 0 | 0 | 0 | 8 |
| Correção | 0 | 6 | 1 | 0 | 0 | 7 |
| Hash | 0 | 3 | 0 | 3 | 0 | 6 |
| Glosa | 3 | 0 | 0 | 0 | 4 | 7 |
| Conciliação | 0 | 4 | 0 | 2 | 0 | 6 |
| Regras | 2 | 0 | 2 | 2 | 0 | 6 |

## Verificação

Cada tarefa inclui uma referência válida e uma resposta incorreta. Os verificadores
determinísticos comparam o resultado sem chamadas a modelos.

## Configuração e reprodução

O runner consulta o catálogo OpenRouter, envia `max_tokens: 16000` e
`usage.include: true`, além de
`temperature: 0` e `seed: 7` quando aceitos pelo modelo. O custo informado vem
do uso reportado pelo provedor. A ferramenta Python roda só com a biblioteca
padrão, sem rede e sem acesso aos arquivos do host, em namespaces Linux isolados;
o limite é de 20 segundos e 4000 caracteres de saída. O agente faz até 16 chamadas
ao modelo por tarefa.

```sh
uv run python -m bench gerar
uv run python -m bench run --modelo provedor/modelo --modo sem_mcp --saida bench/resultados
uv run python -m bench run --modelo provedor/modelo --modo com_mcp --tarefas hash-01
uv run python -m bench tabela bench/resultados
```

Contribuições devem adicionar tarefas sintéticas determinísticas com um
verificador, uma referência que passe e uma resposta incorreta que falhe.

## Limitações

A amostra é pequena, cobre apenas TISS e mede uma execução por tarefa. Os modelos
podem não aceitar os parâmetros de temperatura ou semente, e resultados podem
variar entre execuções.

## Resultados

<!-- resultados -->
