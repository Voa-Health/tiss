# TISS-Bench

Benchmark público e reproduzível de tarefas sintéticas TISS 4.03.00 para comparar
agentes de código com e sem as ferramentas MCP do `tiss`.

As transcrições completas ficam fora do repositório em `.bench/transcricoes/`,
diretório ignorado pelo Git. O repositório mantém apenas `resumo.jsonl` por data
em `bench/resultados/`.

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
uv run python -m bench run --modelo provedor/modelo --modo sem_mcp --saida .bench/transcricoes
uv run python -m bench run --modelo provedor/modelo --modo com_mcp --tarefas hash-01
uv run python -m bench resumir --transcricoes .bench/transcricoes
uv run python -m bench tabela bench/resultados
```

Contribuições devem adicionar tarefas sintéticas determinísticas com um
verificador, uma referência que passe e uma resposta incorreta que falhe.

## Limitações

A amostra é pequena, cobre apenas TISS e mede uma execução por tarefa. Os modelos
podem não aceitar os parâmetros de temperatura ou semente, e resultados podem
variar entre execuções. O limite de 16 chamadas pesa mais nas tarefas de geração.

## Resultados

Rodada de 22/10/2026: 40 tarefas, 4 modelos, 2 modos, uma execução por tarefa. Custo total da rodada: US$ 20,21. Resumo por tarefa em [`resultados/2026-10-22/resumo.jsonl`](resultados/2026-10-22/resumo.jsonl).

### Por categoria

| Modelo | Slug | Data | Modo | Geração | Correção | Hash | Glosa | Conciliação | Regras | Total | Erros de API | Custo (US$) |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GPT-6.1 Sol | `openai/gpt-6.1-sol` | 2026-10-22 | `sem_mcp` | 63% | 86% | 100% | 100% | 100% | 67% | 85% | 0 | 0,80 |
| GPT-6.1 Sol | `openai/gpt-6.1-sol` | 2026-10-22 | `com_mcp` | 25% | 86% | 100% | 100% | 100% | 100% | 83% | 1 | 2,03 |
| Claude Sonnet 5.5 | `anthropic/claude-sonnet-5.5` | 2026-10-22 | `sem_mcp` | 0% | 57% | 67% | 100% | 100% | 67% | 63% | 0 | 1,83 |
| Claude Sonnet 5.5 | `anthropic/claude-sonnet-5.5` | 2026-10-22 | `com_mcp` | 38% | 100% | 100% | 100% | 100% | 100% | 88% | 0 | 9,69 |
| Gemini 3.8 Flash | `google/gemini-3.8-flash` | 2026-10-22 | `sem_mcp` | 0% | 0% | 17% | 86% | 100% | 67% | 43% | 2 | 3,56 |
| Gemini 3.8 Flash | `google/gemini-3.8-flash` | 2026-10-22 | `com_mcp` | 0% | 100% | 100% | 100% | 100% | 83% | 78% | 0 | 1,63 |
| DeepSeek V4.1 Flash | `deepseek/deepseek-v4.1-flash` | 2026-10-22 | `sem_mcp` | 0% | 0% | 0% | 86% | 100% | 67% | 40% | 1 | 0,30 |
| DeepSeek V4.1 Flash | `deepseek/deepseek-v4.1-flash` | 2026-10-22 | `com_mcp` | 0% | 86% | 83% | 100% | 100% | 100% | 75% | 0 | 0,37 |

### Por perspectiva

| Modelo | Modo | Profissional | Prestador | Operadora | Gestor | Paciente | Total |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GPT-6.1 Sol | `sem_mcp` | 86% | 84% | 100% | 71% | 100% | 85% |
| GPT-6.1 Sol | `com_mcp` | 86% | 68% | 100% | 100% | 100% | 83% |
| Claude Sonnet 5.5 | `sem_mcp` | 71% | 47% | 100% | 57% | 100% | 63% |
| Claude Sonnet 5.5 | `com_mcp` | 86% | 79% | 100% | 100% | 100% | 88% |
| Gemini 3.8 Flash | `sem_mcp` | 71% | 21% | 67% | 43% | 75% | 43% |
| Gemini 3.8 Flash | `com_mcp` | 71% | 68% | 100% | 86% | 100% | 78% |
| DeepSeek V4.1 Flash | `sem_mcp` | 71% | 21% | 67% | 29% | 75% | 40% |
| DeepSeek V4.1 Flash | `com_mcp` | 71% | 63% | 100% | 86% | 100% | 75% |

### Média dos quatro modelos

| Modo | Geração | Correção | Hash | Glosa | Conciliação | Regras | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `sem_mcp` | 16% | 36% | 46% | 93% | 100% | 67% | 58% |
| `com_mcp` | 16% | 93% | 96% | 100% | 100% | 96% | 81% |

### Leitura

- Na média dos quatro modelos, o acerto total foi de 58% sem MCP e 81% com MCP.
- Os maiores ganhos foram em correção de lote rejeitado (36% → 93%) e hash do
  epílogo (46% → 96%).
- Claude Sonnet 5.5, Gemini 3.8 Flash e DeepSeek V4.1 Flash ganharam de 25 a 35
  pontos com MCP. GPT-6.1 Sol ficou em 85% sem MCP e 83% com MCP.
- Gerar um lote do zero ficou em 16% nos dois modos. Com MCP, as 27 falhas de
  geração esgotaram as 16 chamadas sem entregar XML.
- Com MCP, a rodada custou US$ 13,72; sem MCP, US$ 6,49.
