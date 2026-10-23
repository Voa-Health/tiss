# Faturista

Agente de referência que fecha o ciclo TISS do prestador sem intervenção humana:
lê os atendimentos, monta e corrige o lote, envia à operadora simulada, lê o
demonstrativo e rascunha o recurso de cada glosa. É feito em
[deepagents](https://github.com/langchain-ai/deepagents) e usa só o MCP público do
tiss.

O mesmo MCP serve operadoras, profissionais, pacientes e gestores; este agente é um
ponto de partida adaptável (por exemplo, troque o fluxo para auditoria de operadora).

![Execução do faturista no terminal](execucao-real/fluxo.gif)

## Início rápido

```sh
git clone https://github.com/Voa-Health/tiss && cd tiss/agents/faturista
export OPENROUTER_API_KEY=...
uv run faturista
```

Sem chave de modelo, `uv run faturista --modelo roteirizado` percorre o mesmo fluxo
com um modelo roteirizado. O resumo sai no terminal e o resultado estruturado em
`resultado.json`. O código de saída é 0 quando o lote é aceito e toda glosa tem
recurso.

## Fluxo

1. `ler_atendimentos` converte CSV, XLSX ou JSON em lote TISS
   ([exemplo sintético](faturista/exemplos/atendimentos.csv)).
2. `tiss_validate` → `tiss_apply_fixes` → `tiss_validate` até o lote ficar válido,
   com no máximo 3 rodadas de correção.
3. `tiss_build` gera o XML 4.03.00.
4. `tiss_sandbox_enviar_lote` envia à operadora simulada e devolve o protocolo.
5. `tiss_sandbox_demonstrativo` e `tiss_parse_demonstrativo` leem as glosas;
   `glosa_explain` as classifica pela Tabela 38.
6. `rascunhar_recurso` registra um recurso por glosa com `needs:
   ["evidencia_clinica"]` e o CTA para o módulo
   [Recurso com evidência clínica](https://tiss-api.voa.health/recurso).

Lotes, XML e protocolos ficam fora do contexto do modelo: as tools devolvem
referências `artefato:N.campo`, que o agente repassa às tools seguintes.

## Configuração

| Variável | Padrão | Uso |
|---|---|---|
| `FATURISTA_MODELO` | `openrouter:anthropic/claude-sonnet-5.5` | `provedor:modelo` |
| `OPENROUTER_API_KEY` | | provedor `openrouter` |
| `OPENAI_API_KEY` | | provedor `openai`, `openai:<modelo>` |
| `ANTHROPIC_API_KEY` | | provedor `anthropic`, `anthropic:<modelo>` |
| `TISS_MCP` | `local` | `local` sobe `python -m tiss.server`; ou uma URL MCP |
| `TISS_API_KEY` | | chave enviada ao MCP remoto |

No MCP remoto (`https://tiss-api.voa.health/mcp`), as tools de sandbox dispensam
chave e as demais exigem `TISS_API_KEY`. Também é possível passar `--modelo`,
`--mcp`, `--cenario` (cenários da operadora simulada, padrão
`carteirinha_vencida`) e `--saida`.

## Como adaptar

- Entrada: mude as colunas em [planilha.py](faturista/planilha.py) para o formato
  do seu sistema, ou entregue o lote já em JSON (`schemas/lote.schema.json`).
- Envio: troque as tools de sandbox pelo webservice da operadora em
  [ferramentas.py](faturista/ferramentas.py).
- Recursos: grave os rascunhos no seu sistema dentro de `rascunhar_recurso`.
- Política: ajuste as instruções em [fluxo.py](faturista/fluxo.py).
- Testes: [roteiro.py](faturista/roteiro.py) emite as tool calls do cenário sem
  LLM; [test_fluxo.py](tests/test_fluxo.py) roda o fluxo completo contra a
  operadora simulada local.

Para comparar modelos no mesmo tipo de tarefa, veja o
[TISS-Bench](../../bench/README.md).

## Execução real

| | |
|---|---|
| Modelo | `anthropic/claude-sonnet-5.5` via OpenRouter |
| Data | 22/10/2026 |
| Chamadas ao modelo | 11 |
| Tokens | 82.526 de entrada, 1.669 de saída |
| Custo | US$ 0,18 pelo preço do catálogo (US$ 2 e US$ 10 por milhão) |
| Resultado | lote 0042 aceito, 1 rodada de correção, 3 glosas 1017, 3 recursos |

[Transcrição](execucao-real/transcricao.txt) ·
[resultado.json](execucao-real/resultado.json)

Se `glosa_explain` não encontrar um código, a glosa segue sem descrição e o recurso
é rascunhado na classe `outra`.

## Desenvolvimento

```sh
uv sync
uv run mypy
uv run pytest
```
