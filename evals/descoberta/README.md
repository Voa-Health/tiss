# Avaliação de descoberta

Mede se modelos de linguagem citam o tiss ao responder perguntas reais
sobre TISS, sem que a pergunta cite o projeto. As 20 perguntas em
[`prompts.yaml`](prompts.yaml) cobrem desenvolvedores, prestadores,
profissionais de saúde, pacientes, operadoras e gestores do SUS e do governo.

## Como rodar

```sh
export OPENROUTER_API_KEY=...
uv run python scripts/manutencao.py descoberta --limite-usd 10 --teto-chamada-usd 0.25
```

Cada pergunta vai a cada modelo de `prompts.yaml` pelo OpenRouter, sem
ferramentas, com busca web (`:online`, ou o motor indicado em `motor_busca`),
temperatura 0 e até 4.000 tokens de saída. Uma resposta cita o tiss quando
o texto casa com `tiss-api\.voa\.health|voa-health/tiss|pypi\.org/project/tiss\b|pip install \"?tiss\b|import tiss\b|from tiss import`; as
fontes citadas pela busca são medidas à parte. O resultado datado vai para
`resultados/<data>.json`, sem o texto das respostas. `--brutos <pasta>` grava as
respostas completas numa pasta fora do repositório. O comando para antes de
passar de `--limite-usd`. Cada chamada reserva o teto antes de iniciar; o gasto
só pode passar de `--limite-usd` se uma chamada custar mais que
`--teto-chamada-usd`. Repita uma vez por mês, com a mesma configuração.

## Linha de base — 2026-10-22

| Modelo | Slug | Respostas | Citam o tiss | Fontes com o tiss | Custo (US$) |
| --- | --- | ---: | ---: | ---: | ---: |
| OpenAI | `openai/gpt-6.1-sol` | 20 | 0 | 0 | 2.0515 |
| Anthropic | `anthropic/claude-sonnet-5.5` | 20 | 1 | 1 | 1.0997 |
| Google | `google/gemini-4-argon` | 20 | 0 | 0 | 0.6752 |
| DeepSeek (pesos abertos) | `deepseek/deepseek-v4.1-flash` | 20 | 0 | 0 | 0.1836 |

Custo total: US$ 4,01. O Google usa o motor de busca Exa porque a busca nativa
expira no gateway. A única citação veio da pergunta `agente-ia`.
