# Registro de alterações

## 0.5.0

- Regras `padrao` usam RE2 com casamento `fullmatch` em tempo linear e rejeitam
  lookaround, backreferences ou UTF-8 inválido com o motivo
  `regex não suportada: …`.
- Pacotes aceitam até 500 regras e regex de até 200 caracteres; valor com mais de
  10 000 caracteres falha a regra `padrao` sem avaliar a regex.
- Pacote publicado da organização que não passa em `validate_package` não executa e
  gera o aviso `op=regras status=422` no log.
- `render_sadt`, `render_html` e `build_context` recebem o logo em `logo` (bytes ou `Path` de PNG ou JPEG), embutido no PDF; outros formatos levantam `ValueError`, e o renderizador só resolve URIs `data:`.
- CLI e clientes do servidor hospedado seguem redirects só para a mesma origem (esquema, host e porta); outra origem levanta `RedirecionamentoRecusado` sem reenviar a credencial.
- API hospedada aceita chaves `sk_voa_` da organização, válidas para os produtos da Voa; `sk_tiss_` continuam aceitas.
- `schemas/mcp-tools.json` registra o manifest `tools/list` do MCP; mudanças em nome, descrição ou esquema de uma ferramenta aparecem no diff.

## 0.4.0

- Action GitHub `Voa-Health/tiss@v0` para validar XML TISS.
- Hook pre-commit `tiss-validate` para validar XML TISS.
- MCP local no registro oficial, com pacote PyPI e transporte stdio em `server.json`.
- A CLI `tiss` oferece `validate`, `fix`, `hash`, `glosa`, `tuss`, `operadora`,
  `mapa`, `mcp` e `serve`; os códigos de saída distinguem sucesso, achados e uso
  inválido, e `validate --format github` gera comandos do GitHub Actions.
- `tiss mcp` inicia um servidor MCP local em stdio; instale o extra opcional
  com `pip install "tiss[mcp]"`.
- A distribuição Python passa a se chamar `tiss`: instale com `pip install tiss`
  e importe com `import tiss`.
- As variáveis de ambiente passam a usar o prefixo `TISS_*`, sem alias de
  compatibilidade.
- `voa-tiss` 0.3.x continua disponível no PyPI, mas não receberá novas versões:
  https://pypi.org/project/voa-tiss/.
- A API hospedada aceita chaves `sk_tiss_` da organização, com escopo por operação,
  revogação em até 60 segundos e uso registrado por chamada.
- TISS-Bench: 40 tarefas sintéticas com verificação determinística e resultados
  de quatro modelos com e sem o MCP.
- Ferramentas MCP passam a usar esquemas de entrada com objeto no topo, compatíveis
  com clientes como Claude.
- Guias de consulta geradas por `build_lote` seguem a ordem definida pelo XSD.
- A validação identifica divergências no hash do epílogo.
