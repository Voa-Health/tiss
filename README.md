# voa-tiss

[![CI](https://github.com/Voa-Health/tiss/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Voa-Health/tiss/actions/workflows/ci.yml) [![PyPI](https://img.shields.io/pypi/v/voa-tiss)](https://pypi.org/project/voa-tiss/) [![Licença](https://img.shields.io/badge/licen%C3%A7a-Apache--2.0-blue)](LICENSE)

**TISS sem dor de cabeça.** Valide, corrija e gere lotes TISS, entenda glosas e
concilie demonstrativos, tudo em código aberto: uma biblioteca Python que roda
offline, uma API HTTP e um MCP remoto para o seu agente de IA.

![Agente faturista fechando o ciclo TISS no terminal: valida o lote, corrige, envia à operadora simulada, lê as glosas e rascunha os recursos](https://raw.githubusercontent.com/Voa-Health/tiss/main/agents/faturista/execucao-real/fluxo.gif)

<sub>O [agente faturista](agents/faturista/README.md) usando só o MCP público:
corrige dois erros do lote, envia à operadora simulada, lê as glosas do
demonstrativo e rascunha um recurso por guia, sem inventar evidência.</sub>

## Para quem é

- **Prestadores** (hospitais, clínicas e laboratórios): pegue o erro antes da
  operadora e saiba por que uma guia foi glosada.
- **Profissionais de saúde:** confira guias e códigos TUSS sem decorar o manual.
- **Operadoras:** audite lotes com as suas regras e publique-as para quem envia.
- **Pacientes:** entenda em linguagem simples o que uma glosa significa.
- **Gestores do SUS e do governo:** consulte dados abertos da ANS sobre perfil de
  operadoras, glosas e rede hospitalar.

## Início rápido

**Python** (3.10+):

```sh
pip install voa-tiss
```

```python
from voa_tiss import examples, validate

report = validate(examples.load("lote-com-erros"))
[(finding.code, finding.severity) for finding in report.findings]
```

**Agente de IA:** conecte o MCP e peça em português, por exemplo "valide este
lote e corrija o que der".

```sh
claude mcp add --transport http voa-tiss https://tiss-api.voa.health/mcp
```

Codex, Cursor, a skill e os plugins estão em [Conectar agentes](#conectar-agentes).

**Navegador:** experimente o playground e a documentação em
[tiss-api.voa.health](https://tiss-api.voa.health).

## Como funciona

Você não precisa escrever XML TISS à mão. O ciclo é sempre o mesmo:

1. **Valide** o lote (`check` ou `validate`). Cada achado traz um código estável,
   a localização e, quando possível, a correção pronta.
2. **Corrija** com `apply_fixes`. As correções são determinísticas, em JSON Patch.
3. **Revalide** até zerar os erros. Se faltar algum dado, `needs` diz exatamente
   qual perguntar.
4. **Gere** o XML com `build_lote` e calcule o hash do epílogo com `hash_epilogo`.

Depois do envio, `parse_demonstrativo` lê o retorno da operadora, `glosa`
explica cada código da Tabela 38 e `plan_reconciliation` concilia o que foi pago
com o que foi cobrado. Para testar sem operadora real, use a
[operadora simulada](docs/tutoriais/06-operadora-simulada.ipynb).

## Por que confiar

- **Offline e determinístico:** validar, corrigir e gerar roda na sua máquina,
  sem telemetria; a mesma entrada dá sempre a mesma saída.
- **XSD fixado por hash:** a validação usa o esquema TISS oficial, conferido
  por hash.
- **À prova de prompt injection:** texto livre da guia é dado, nunca instrução.
- **Seus dados não ficam com a gente:** a API não armazena nem registra payloads
  e não os usa para treinar modelos.
- **Medido:** no [TISS-Bench](bench/README.md), 40 tarefas sintéticas e quatro
  modelos, o acerto médio subiu de 58% sem o MCP para 81% com ele.

## Aprenda com os tutoriais

- [Validar um lote](docs/tutoriais/01-validar-um-lote.ipynb)
- [Demonstrativo e conciliação](docs/tutoriais/02-demonstrativo-e-conciliacao.ipynb)
- [TUSS e SP/SADT](docs/tutoriais/03-tuss-e-sp-sadt.ipynb)
- [Gerar e corrigir um lote](docs/tutoriais/04-gerar-e-corrigir-um-lote.ipynb)
- [Regras por operadora](docs/tutoriais/05-regras-por-operadora.ipynb)
- [Operadora simulada](docs/tutoriais/06-operadora-simulada.ipynb)
- [Agente faturista](agents/faturista/README.md): um agente completo para
  adaptar ao seu fluxo.

## Conectar agentes

O MCP remoto fica em `https://tiss-api.voa.health/mcp`. Agentes encontram as
instruções de uso no [AGENTS.md](AGENTS.md) e na
[skill voa-tiss](skills/voa-tiss/SKILL.md).

```sh
npx skills add Voa-Health/tiss
claude plugin marketplace add Voa-Health/tiss && claude plugin install voa-tiss@voa-tiss
codex plugin marketplace add Voa-Health/tiss
```

No Codex, adicione a `~/.codex/config.toml`:

```toml
[mcp_servers.voa-tiss]
url = "https://tiss-api.voa.health/mcp"
```

No Cursor, adicione ao `mcp.json`:

```json
{
  "mcpServers": {
    "voa-tiss": {
      "url": "https://tiss-api.voa.health/mcp"
    }
  }
}
```

## API HTTP

Instale o extra do servidor e inicie a API local:

```sh
pip install "voa-tiss[server]"
python -m voa_tiss.server --host 127.0.0.1 --port 8000
```

Valide XML como JSON ou como corpo XML:

```sh
python -c 'import json, pathlib; print(json.dumps({"xml": pathlib.Path("lote.xml").read_text()}))' \
  | curl https://tiss-api.voa.health/v1/validate \
  -H 'Content-Type: application/json' \
  --data-binary @-
curl https://tiss-api.voa.health/v1/validate \
  -H 'Content-Type: application/xml' \
  --data-binary @lote.xml
```

Consulte o [OpenAPI](https://tiss-api.voa.health/openapi.json) e o
[catálogo de operações](docs/api.md).

Sem chave, só as operações do sandbox respondem. Para as demais, entre com a
conta Voa em [tiss-api.voa.health/chaves](https://tiss-api.voa.health/chaves) e
envie a chave recebida. Não há limite diário.

```sh
curl https://tiss-api.voa.health/v1/validate \
  -H "Authorization: Bearer $VOA_TISS_API_KEY" \
  -H 'Content-Type: application/xml' \
  --data-binary @lote.xml
```

A chave vale 24 horas. Renove com o `refresh_token` recebido no login; chave
inválida ou expirada retorna `401`:

```sh
curl https://tiss-api.voa.health/v1/keys/refresh \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token": "..."}'
```

O serviço não armazena nem registra payloads e não os usa para treinar modelos.
Quando ativada por `POSTHOG_KEY`, a telemetria agregada contém operação,
códigos de achados, registro ANS, versão TISS e data; na emissão de chave,
inclui nível e identificador da organização, sem e-mail. Envie
`X-Voa-Telemetry: off` para desativá-la. A biblioteca local permanece offline e
nunca envia telemetria. `VOA_TISS_API_KEY` é a variável que clientes HTTP locais
podem ler para enviar uma chave de acesso.

## Referência da biblioteca

Para renderizar a guia SP/SADT em PDF, instale `pip install "voa-tiss[pdf]"`.

| Símbolo | Uso |
| --- | --- |
| `validate` | Valida um lote TISS e retorna um relatório. |
| `check` | Verifica um lote JSON e propõe correções. |
| `apply_fixes` | Aplica correções determinísticas ao lote JSON. |
| `build_lote` | Gera o XML TISS a partir de um lote validado. |
| `parse_lote` | Converte XML TISS em um lote JSON. |
| `audit` | Audita o lote com o contexto da operadora. |
| `hash_epilogo` | Calcula o hash do epílogo. |
| `glosa` | Consulta um código da Tabela 38. |
| `dominio.lookup` / `dominio.search` | Consulta tabelas de domínio TISS. |
| `operadoras.lookup` / `operadoras.search` | Consulta operadoras ativas na ANS. |
| `operadoras.perfil` | Junta o cadastro e os indicadores de glosa da ANS. |
| `parse_demonstrativo` | Lê um demonstrativo e retorna decisões por guia. |
| `plan_reconciliation` | Propõe conciliação entre decisões e guias. |
| `sadt_missing` | Lista campos obrigatórios ausentes da guia SP/SADT. |
| `sadt_catalog` | Retorna uma cópia do catálogo SP/SADT. |
| `render_sadt` (extra `pdf`) | Gera um PDF da guia SP/SADT. |
| `tuss.lookup` | Consulta um código TUSS. |
| `tuss.search` | Busca registros TUSS por texto. |
| `rede.*` | Consulta vínculos da rede hospitalar da ANS. |
| `json_schema` | Retorna o esquema JSON de um tipo público. |
| `examples` | Disponibiliza exemplos sintéticos do pacote. |

`voa_tiss.rede` baixa e verifica os dados na primeira consulta. Defina
`VOA_TISS_REDE` com o caminho de um SQLite local para usar uma cópia própria.

### Achados

| Campo | Significado |
| --- | --- |
| `code` | Código estável em [docs/codigos.md](docs/codigos.md) |
| `severity` | `error` ou `warning` |
| `guia` | Identificador da guia, quando houver |
| `xpath` | Localização no XML, quando houver |
| `message` | Descrição concisa do achado |
| `pointer` | JSON Pointer no lote JSON, quando houver |
| `fix` | Correção em JSON Patch, quando determinística |
| `needs` | Campos necessários para completar a guia |
| `glosa` | Código provável da Tabela 38, quando houver |
| `rule` | Regra de operadora que gerou o achado, quando houver |

## Mais

- [TISS-Bench: agentes com e sem o MCP](bench/README.md)
- [Esquemas JSON](schemas/)
- [Fontes de dados](DATA_SOURCES.md)
- [Contribuição](CONTRIBUTING.md)
- [Licença Apache-2.0](LICENSE)
