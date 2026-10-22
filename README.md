<div align="center">
  <a href="https://tiss-api.voa.health">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset=".github/images/logo-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset=".github/images/logo-light.svg">
      <img alt="Voa" src="https://raw.githubusercontent.com/Voa-Health/tiss/main/.github/images/logo-light.svg" width="160">
    </picture>
  </a>
</div>

<div align="center">
  <h3>TISS sem dor de cabeça, para pessoas e agentes de IA.</h3>
</div>

<div align="center">
  <a href="https://github.com/Voa-Health/tiss/actions/workflows/ci.yml"><img src="https://github.com/Voa-Health/tiss/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <a href="https://pypi.org/project/voa-tiss/"><img src="https://img.shields.io/pypi/v/voa-tiss?label=PyPI" alt="Versão no PyPI"></a>
  <a href="https://pypi.org/project/voa-tiss/"><img src="https://img.shields.io/pypi/pyversions/voa-tiss" alt="Versões do Python"></a>
  <a href="https://github.com/Voa-Health/tiss/blob/main/LICENSE"><img src="https://img.shields.io/badge/licen%C3%A7a-Apache--2.0-blue" alt="Licença Apache-2.0"></a>
  <a href="https://registry.modelcontextprotocol.io/v0/servers?search=health.voa/tiss"><img src="https://img.shields.io/badge/MCP-health.voa%2Ftiss-7c3aed" alt="MCP Registry"></a>
</div>

<div align="center">
  <a href="https://tiss-api.voa.health">Site</a> ·
  <a href="https://tiss-api.voa.health/playground">Playground</a> ·
  <a href="https://tiss-api.voa.health/docs">Documentação</a> ·
  <a href="https://tiss-api.voa.health/operadoras">Operadoras</a> ·
  <a href="https://github.com/Voa-Health/tiss/blob/main/bench/README.md">TISS-Bench</a>
</div>

<br>

Valide, corrija e gere lotes TISS, entenda glosas e concilie demonstrativos, tudo
em código aberto: uma biblioteca Python que roda offline, uma API HTTP e um MCP
remoto para o seu agente de IA.

<div align="center">
  <img src="https://raw.githubusercontent.com/Voa-Health/tiss/main/agents/faturista/execucao-real/fluxo.gif" alt="Agente faturista fechando o ciclo TISS no terminal: valida o lote, corrige, envia à operadora simulada, lê as glosas e rascunha os recursos" width="820">
  <br>
  <sub>O <a href="https://github.com/Voa-Health/tiss/blob/main/agents/faturista/README.md">agente faturista</a> usando só o MCP público: corrige dois erros do lote, envia à operadora simulada, lê as glosas e rascunha um recurso por guia, sem inventar evidência.</sub>
</div>

> [!TIP]
> Usa Claude Code, Codex ou Cursor? Conecte o MCP e peça em português, por
> exemplo "valide este lote e corrija o que der". Veja
> [Conectar agentes](#conectar-agentes).

## Início rápido

```sh
pip install voa-tiss
```

```python
from voa_tiss import examples, validate

report = validate(examples.load("lote-com-erros"))
[(finding.code, finding.severity) for finding in report.findings]
```

Cada achado traz um código estável, a localização e, quando possível, a correção
pronta. Requer Python 3.10+.

Prefere testar no navegador? Abra o
[playground](https://tiss-api.voa.health/playground).

## Para quem é

| Você é | O voa-tiss ajuda a |
| --- | --- |
| **Prestador** (hospital, clínica, laboratório) | pegar o erro antes da operadora e entender por que uma guia foi glosada |
| **Profissional de saúde** | conferir guias e códigos TUSS sem decorar o manual |
| **Operadora** | auditar lotes com as suas regras e publicá-las para quem envia |
| **Paciente** | entender em linguagem simples o que uma glosa significa |
| **Gestor do SUS ou do governo** | consultar dados abertos da ANS sobre operadoras, glosas e rede hospitalar |

## Como funciona

Você não precisa escrever XML TISS à mão. O ciclo é sempre o mesmo:

1. **Valide** o lote com `check` ou `validate`.
2. **Corrija** com `apply_fixes`: as correções são determinísticas, em JSON Patch.
3. **Revalide** até zerar os erros. Se faltar algum dado, `needs` diz exatamente
   qual perguntar.
4. **Gere** o XML com `build_lote` e calcule o hash do epílogo com `hash_epilogo`.

Depois do envio, `parse_demonstrativo` lê o retorno da operadora, `glosa` explica
cada código da Tabela 38 e `plan_reconciliation` concilia o que foi pago com o
que foi cobrado. Para testar sem operadora real, use a
[operadora simulada](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/06-operadora-simulada.ipynb).

## O que vem no pacote

- **[Biblioteca Python](#referência)**: validação, correção, geração, hash,
  auditoria, demonstrativos, TUSS, operadoras e rede hospitalar.
- **[API HTTP](#api-http)**: as mesmas operações em
  `https://tiss-api.voa.health`, com [OpenAPI](https://tiss-api.voa.health/openapi.json).
- **[MCP remoto](#conectar-agentes)**: 20 ferramentas e 3 prompts para agentes,
  no [registro oficial de MCP](https://registry.modelcontextprotocol.io/v0/servers?search=health.voa/tiss).
- **[Operadora simulada](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/06-operadora-simulada.ipynb)**: envie
  lotes e receba protocolo, demonstrativo e glosas sem tocar em produção.
- **[Agente faturista](https://github.com/Voa-Health/tiss/blob/main/agents/faturista/README.md)**: um agente completo para
  adaptar ao seu fluxo.
- **[TISS-Bench](https://github.com/Voa-Health/tiss/blob/main/bench/README.md)**: 40 tarefas sintéticas para medir agentes com
  e sem o MCP.

## Por que confiar

- **Offline e determinístico:** validar, corrigir e gerar roda na sua máquina,
  sem telemetria; a mesma entrada dá sempre a mesma saída.
- **XSD fixado por hash:** a validação usa o esquema TISS oficial, conferido por
  hash.
- **À prova de prompt injection:** texto livre da guia é dado, nunca instrução.
- **Seus dados não ficam com a gente:** veja a política de payloads e telemetria
  em [API HTTP](#api-http).
- **Medido:** no [TISS-Bench](https://github.com/Voa-Health/tiss/blob/main/bench/README.md), com quatro modelos, o acerto
  médio subiu de 58% sem o MCP para 81% com ele. Gerar um lote do zero ainda fica
  em 16% nos dois modos.

## Conectar agentes

O MCP remoto fica em `https://tiss-api.voa.health/mcp`. Agentes encontram as
instruções de uso no [AGENTS.md](https://github.com/Voa-Health/tiss/blob/main/AGENTS.md) e na
[skill voa-tiss](https://github.com/Voa-Health/tiss/blob/main/skills/voa-tiss/SKILL.md).

```sh
claude mcp add --transport http voa-tiss https://tiss-api.voa.health/mcp
```

<details>
<summary><strong>Skill, plugins, Codex e Cursor</strong></summary>

### Skill, plugins, Codex e Cursor

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

</details>

## Tutoriais

| Tutorial | O que você aprende |
| --- | --- |
| [Validar um lote](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/01-validar-um-lote.ipynb) | ler achados e corrigir |
| [Demonstrativo e conciliação](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/02-demonstrativo-e-conciliacao.ipynb) | conferir o que a operadora pagou |
| [TUSS e SP/SADT](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/03-tuss-e-sp-sadt.ipynb) | buscar códigos e montar a guia |
| [Gerar e corrigir um lote](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/04-gerar-e-corrigir-um-lote.ipynb) | sair do JSON para o XML válido |
| [Regras por operadora](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/05-regras-por-operadora.ipynb) | auditar com regras publicadas |
| [Operadora simulada](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/06-operadora-simulada.ipynb) | testar envios e glosas |

## API HTTP

<details>
<summary><strong>Servidor local, chaves e telemetria</strong></summary>

### Servidor local, chaves e telemetria

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
[catálogo de operações](https://github.com/Voa-Health/tiss/blob/main/docs/api.md).

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

</details>

## Referência

<details>
<summary><strong>Símbolos da biblioteca</strong></summary>

### Símbolos da biblioteca

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

</details>

<details>
<summary><strong>Campos de um achado</strong></summary>

### Campos de um achado

| Campo | Significado |
| --- | --- |
| `code` | Código estável em [docs/codigos.md](https://github.com/Voa-Health/tiss/blob/main/docs/codigos.md) |
| `severity` | `error` ou `warning` |
| `guia` | Identificador da guia, quando houver |
| `xpath` | Localização no XML, quando houver |
| `message` | Descrição concisa do achado |
| `pointer` | JSON Pointer no lote JSON, quando houver |
| `fix` | Correção em JSON Patch, quando determinística |
| `needs` | Campos necessários para completar a guia |
| `glosa` | Código provável da Tabela 38, quando houver |
| `rule` | Regra de operadora que gerou o achado, quando houver |

</details>

## Mais

- [Esquemas JSON](https://github.com/Voa-Health/tiss/tree/main/schemas/) · [Fontes de dados](https://github.com/Voa-Health/tiss/blob/main/DATA_SOURCES.md) ·
  [Changelog](https://github.com/Voa-Health/tiss/blob/main/CHANGELOG.md)
- [Contribuição](https://github.com/Voa-Health/tiss/blob/main/CONTRIBUTING.md) · [Código de conduta](https://github.com/Voa-Health/tiss/blob/main/CODE_OF_CONDUCT.md) ·
  [Segurança](https://github.com/Voa-Health/tiss/blob/main/SECURITY.md)
- [Licença Apache-2.0](https://github.com/Voa-Health/tiss/blob/main/LICENSE)
