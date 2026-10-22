# MCP

O endpoint remoto usa Streamable HTTP: `https://tiss-api.voa.health/mcp`.
Sem chave, estão disponíveis apenas as ferramentas `tiss_sandbox_*`. Para as
demais, envie `Authorization: Bearer <chave>` obtida no serviço.

## Exemplos de chamadas

Validar XML:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "tiss_validate",
    "arguments": {"xml": "<mensagem>…</mensagem>"}
  }
}
```

Validar lote e aplicar patch:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "tiss_validate",
    "arguments": {"lote": {}}
  }
}
```

Passe o lote e o relatório retornado à ferramenta `tiss_apply_fixes`, depois
revalide com `tiss_validate`. Consulte o esquema do lote em
`tiss://schemas/lote`.

## Clientes

Claude Code:

```sh
claude mcp add --transport http voa-tiss https://tiss-api.voa.health/mcp
```

Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.voa-tiss]
url = "https://tiss-api.voa.health/mcp"
```

Cursor (`mcp.json`):

```json
{
  "mcpServers": {
    "voa-tiss": {
      "url": "https://tiss-api.voa.health/mcp"
    }
  }
}
```
