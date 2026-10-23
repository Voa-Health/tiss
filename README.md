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
  <a href="https://pypi.org/project/tiss/"><img src="https://img.shields.io/pypi/v/tiss?label=PyPI" alt="Versão no PyPI"></a>
  <a href="https://pypi.org/project/tiss/"><img src="https://img.shields.io/pypi/pyversions/tiss" alt="Versões do Python"></a>
  <a href="https://github.com/Voa-Health/tiss/blob/main/LICENSE"><img src="https://img.shields.io/badge/licen%C3%A7a-Apache--2.0-blue" alt="Licença Apache-2.0"></a>
  <a href="https://registry.modelcontextprotocol.io/v0/servers?search=health.voa/tiss"><img src="https://img.shields.io/badge/MCP-health.voa%2Ftiss-7c3aed" alt="MCP Registry"></a>
</div>

<div align="center">
  <a href="https://tiss-api.voa.health">Site</a> ·
  <a href="https://tiss-api.voa.health/playground">Playground</a> ·
  <a href="https://docs.voa.health/integracao/tiss">Documentação</a> ·
  <a href="https://tiss-api.voa.health/operadoras">Operadoras</a> ·
  <a href="https://github.com/Voa-Health/tiss/blob/main/bench/README.md">TISS-Bench</a>
</div>

<br>

Valide, corrija e gere lotes TISS, entenda glosas e concilie demonstrativos, tudo
em código aberto: uma biblioteca Python que roda offline, uma API HTTP e um MCP
remoto para o seu agente de IA.

<div align="center">
  <img src="https://raw.githubusercontent.com/Voa-Health/tiss/main/web/public/demos/cli.gif" alt="Terminal: tiss validate aprova o lote e confere o hash, o código do procedimento sai do lote para tiss tuss e o código da glosa sai do demonstrativo para tiss glosa" width="820">
  <br>
  <sub>A CLI <code>tiss</code> valida o lote, consulta o procedimento cobrado e explica a glosa que voltou no demonstrativo, tudo offline. Para ver um agente fechando o ciclo, veja o <a href="https://github.com/Voa-Health/tiss/blob/main/agents/faturista/README.md">agente faturista</a>.</sub>
</div>

<!-- mcp-name: health.voa/tiss -->

> [!TIP]
> Usa Claude Code, Codex ou Cursor? Conecte o MCP e peça em português, por
> exemplo "valide este lote e corrija o que der". Veja
> [Conectar agentes](#conectar-agentes).

## Início rápido

```sh
pip install tiss
```

```python
from tiss import examples, validate

report = validate(examples.load("lote-com-erros"))
[(finding.code, finding.severity) for finding in report.findings]
```

Cada achado traz um código estável, a localização e, quando possível, a correção
pronta. Requer Python 3.10+.

Prefere testar no navegador? Abra o
[playground](https://tiss-api.voa.health/playground).

## CLI

Instale a CLI com `pip install tiss` ou execute sem instalar com
`uvx tiss validate lote.xml`.

| Comando | Uso |
| --- | --- |
| `tiss validate <paths...>` | Valida arquivos XML/JSON ou pastas. Use `--operadora REGISTRO` para aplicar regras. |
| `tiss fix <arquivo>` | Mostra um diff; use `--write` ou `-o CAMINHO` para gravar. |
| `tiss hash <arquivo>` | Calcula o hash; `--check` compara com o epílogo. |
| `tiss glosa <código>` | Consulta a Tabela 38. |
| `tiss tuss <código\|termo>` | Busca códigos e descrições TUSS. |
| `tiss operadora <registro>` | Consulta o perfil da operadora. |
| `tiss mapa <pasta>` | Gera o mapa agregado de rejeição. |
| `tiss mcp` | Inicia o MCP local em stdio; requer `tiss[mcp]`. |
| `tiss serve` | Inicia a API HTTP local; requer `tiss[server]`. |

Os códigos de saída são `0` para sucesso, `1` para achados ou itens não
encontrados e `2` para uso inválido ou entrada ilegível. Para integração com
GitHub Actions, use `tiss validate --format github lote.xml`.

## Para quem é

| Você é | O tiss ajuda a |
| --- | --- |
| **Prestador** (hospital, clínica, laboratório) | pegar o erro antes da operadora e entender por que uma guia foi glosada |
| **Profissional de saúde** | conferir guias e códigos TUSS sem decorar o manual |
| **Operadora** | checar lotes na entrada com as suas regras, offline; ver o mapa de rejeição por prestador; oferecer sandbox com as suas regras; validar autorizações TISS; publicar regras com selo Oficial; e, nos módulos com agente, analisar contas e autorizações prévias |
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
  auditoria, demonstrativos, TUSS, operadoras, rede hospitalar e referência D-TISS.
- **[API HTTP](#api-http)**: as mesmas operações em
  `https://tiss-api.voa.health`, com [OpenAPI](https://tiss-api.voa.health/openapi.json).
- **[MCP remoto](#conectar-agentes)**: 25 ferramentas e 3 prompts para agentes,
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

O MCP local roda offline e mantém as guias na máquina:

```sh
claude mcp add tiss -- uvx --from "tiss[mcp]" tiss mcp
```

Para usar o serviço remoto:

```sh
claude mcp add --transport http tiss https://tiss-api.voa.health/mcp
```

Agentes encontram instruções em
[AGENTS.md](https://github.com/Voa-Health/tiss/blob/main/AGENTS.md) e na
[skill tiss](https://github.com/Voa-Health/tiss/blob/main/skills/tiss/SKILL.md).

### Skill, plugins, Codex e Cursor

<details>
<summary>Ver detalhes</summary>

```sh
npx skills add Voa-Health/tiss
claude plugin marketplace add Voa-Health/tiss && claude plugin install tiss@tiss
codex plugin marketplace add Voa-Health/tiss
```

No Codex, adicione a `~/.codex/config.toml` para o MCP local:

```toml
[mcp_servers.tiss]
command = "uvx"
args = ["--from", "tiss[mcp]", "tiss", "mcp"]
```

Para usar o serviço remoto:

```toml
[mcp_servers.tiss]
url = "https://tiss-api.voa.health/mcp"
```

No Cursor, adicione ao `mcp.json` para o MCP local:

```json
{
  "mcpServers": {
    "tiss": {
      "command": "uvx",
      "args": ["--from", "tiss[mcp]", "tiss", "mcp"]
    }
  }
}
```

Para usar o serviço remoto:

```json
{
  "mcpServers": {
    "tiss": {
      "url": "https://tiss-api.voa.health/mcp"
    }
  }
}
```

</details>

### Privacidade

CLI, MCP local, Action e hook rodam na sua máquina ou runner, sem chave, registro
de uso ou telemetria. As chamadas de rede do pacote são feitas apenas por
ferramentas `rede`/D-TISS, que baixam dados públicos, e `sandbox_*`, que usam a
operadora simulada.

## CI e pre-commit

Use a Action para validar lotes no GitHub Actions:

```yaml
- uses: Voa-Health/tiss@v0
  with:
    paths: lotes/
```

O input opcional `operadora` aplica as regras locais dessa operadora. Para
instalar o hook, adicione ao `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/Voa-Health/tiss
    rev: v0.4.0
    hooks:
      - id: tiss-validate
```

### Sem assets opcionais

A Action e o hook instalam apenas `tiss` (com `lxml`) e validam com os XSD 4.02.00
e 4.03.00 incluídos no pacote. Não instalam `pdf` nem baixam dados de `rede`/D-TISS;
fora o download do pacote, nada vai à rede. `operadora` aplica apenas regras
incluídas no pacote. O hook seleciona arquivos `.xml`; limite-o com `files:` se
o repositório tiver outros XML.

## Tutoriais

| Tutorial | O que você aprende |
| --- | --- |
| [Validar um lote](https://docs.voa.health/integracao/tiss/tutoriais/01-validar-um-lote) ([notebook](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/01-validar-um-lote.ipynb)) | ler achados e corrigir |
| [Demonstrativo e conciliação](https://docs.voa.health/integracao/tiss/tutoriais/02-demonstrativo-e-conciliacao) ([notebook](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/02-demonstrativo-e-conciliacao.ipynb)) | conferir o que a operadora pagou |
| [TUSS e SP/SADT](https://docs.voa.health/integracao/tiss/tutoriais/03-tuss-e-sp-sadt) ([notebook](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/03-tuss-e-sp-sadt.ipynb)) | buscar códigos e montar a guia |
| [Gerar e corrigir um lote](https://docs.voa.health/integracao/tiss/tutoriais/04-gerar-e-corrigir-um-lote) ([notebook](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/04-gerar-e-corrigir-um-lote.ipynb)) | sair do JSON para o XML válido |
| [Regras por operadora](https://docs.voa.health/integracao/tiss/tutoriais/05-regras-por-operadora) ([notebook](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/05-regras-por-operadora.ipynb)) | auditar com regras publicadas |
| [Operadora simulada](https://docs.voa.health/integracao/tiss/tutoriais/06-operadora-simulada) ([notebook](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/06-operadora-simulada.ipynb)) | testar envios e glosas |
| [Autorização SP/SADT](https://docs.voa.health/integracao/tiss/tutoriais/07-autorizacao) ([notebook](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/07-autorizacao.ipynb)) | solicitar e analisar autorizações |
| [Mapa de rejeição](https://docs.voa.health/integracao/tiss/tutoriais/08-mapa-de-rejeicao) ([notebook](https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/08-mapa-de-rejeicao.ipynb)) | agregar achados por prestador |

## API HTTP

### Servidor local, chaves e telemetria

<details>
<summary>Ver detalhes</summary>

Instale o extra do servidor e inicie a API local:

```sh
pip install "tiss[server]"
tiss serve --host 127.0.0.1 --port 8000
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

Sem chave, só as operações do sandbox respondem. Para as demais, crie uma chave
`sk_tiss_` no [painel da organização](https://tiss-api.voa.health/org) e envie-a
em `Authorization: Bearer`. Não há limite diário.

```sh
curl https://tiss-api.voa.health/v1/validate \
  -H "Authorization: Bearer $TISS_API_KEY" \
  -H 'Content-Type: application/xml' \
  --data-binary @lote.xml
```

Chave inválida ou revogada retorna `401`, e a revogação vale em até 60 segundos.
Chave sem o escopo da operação (`tiss:validate`, `tiss:build`, `tiss:sandbox`,
`tiss:accounts`, `tiss:authorization` ou `tiss:rules`) retorna `403`. Cada
chamada com chave entra no uso da organização, por operação e por chave.
Auto-hospedado, sem `TISS_BACKEND_URL` e `TISS_SERVICE_SECRET`, o
servidor não exige chave.

O serviço não armazena nem registra payloads e não os usa para treinar modelos.
Quando ativada por `POSTHOG_KEY`, a telemetria agregada contém operação,
códigos de achados, registro ANS, versão TISS e data, sem e-mail. Envie
`X-Voa-Telemetry: off` para desativá-la. A biblioteca local permanece offline e
nunca envia telemetria. `TISS_API_KEY` é a variável que clientes HTTP locais
podem ler para enviar uma chave de acesso.

O mapa de rejeição hospedado é uma coleta separada, opt-in e desligada por padrão.
Quando habilitado no `/org`, envia somente agregados por prestador, código, regra e mês.
O CPF é pseudonimizado com HMAC e segredo próprio da organização antes de sair do cliente;
o CNPJ permanece em claro, e o código do prestador na operadora tem preferência.
A retenção é de 24 meses, e a organização pode desligar a coleta e apagar tudo no `/org`.
A telemetria anônima permanece independente e não muda com esse aceite.

Na CLI, `mapa --enviar` usa `TISS_KEY` e envia ao servidor público.
`TISS_MAPA_URL` substitui a URL de envio (padrão:
`https://tiss-api.voa.health/v1/rejection-map/submit`). Sem
`TISS_SEGREDO_PSEUDONIMO`, a CLI busca o segredo antes de agregar, via
`GET /v1/rejection-map/config`, no mesmo servidor e com Bearer sk_tiss_.
O envio usa `POST /v1/rejection-map/submit`, com o mapa agregado como corpo JSON.

</details>

## Referência

### Símbolos da biblioteca

<details>
<summary>Ver detalhes</summary>

Para renderizar a guia SP/SADT em PDF, instale `pip install "tiss[pdf]"`.

| Símbolo | Uso |
| --- | --- |
| `validate` | Valida um lote TISS e retorna um relatório. |
| `check` | Verifica um lote JSON e propõe correções. |
| `apply_fixes` | Aplica correções determinísticas ao lote JSON. |
| `build_lote` | Gera o XML TISS a partir de um lote validado. |
| `parse_lote` | Converte XML TISS em um lote JSON. |
| `audit` | Audita o lote com o contexto da operadora. |
| `validate_package` | Valida um pacote de regras de operadora e lista os erros. |
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
| `tiss_referencia` | Consulta valores unitários de referência D-TISS da ANS por TUSS. |
| `json_schema` | Retorna o esquema JSON de um tipo público. |
| `examples` | Disponibiliza exemplos sintéticos do pacote. |

`tiss.rede` baixa e verifica os dados na primeira consulta. Defina
`TISS_REDE` com o caminho de um SQLite local para usar uma cópia própria.
`tiss.referencia` consulta valores unitários de referência da ANS por TUSS, UF e
semestre; o valor pago é somente o pago diretamente ao fornecedor, não o total
pago pela operadora. Defina `TISS_REFERENCIA` para usar um SQLite local.

</details>

### Campos de um achado

<details>
<summary>Ver detalhes</summary>

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
