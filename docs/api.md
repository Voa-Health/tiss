# API HTTP e MCP

Orçamento aproximado: `ceil(tamanho UTF-8 do JSON / 4)` tokens.

| Operação | Rota HTTP | Tool MCP | Descrição | Orçamento |
| --- | --- | --- | --- | ---: |
| `validate` | `POST /v1/validate` | `tiss_validate` | Valida um XML TISS. Quando usar: antes de enviar um lote. Quando não usar: para interpretar glosas. | 2500 |
| `parse_demonstrativo` | `POST /v1/parse_demonstrativo` | `tiss_parse_demonstrativo` | Lê decisões de um demonstrativo. Quando usar: para identificar pagamentos e glosas. Quando não usar: para validar lotes. | 1800 |
| `plan_reconciliation` | `POST /v1/plan_reconciliation` | `tiss_plan_reconciliation` | Propõe vínculos entre decisões e guias. Quando usar: após ler um demonstrativo. Quando não usar: para alterar guias. | 3000 |
| `tuss_lookup` | `POST /v1/tuss_lookup` | `tuss_lookup` | Busca um código TUSS exato. Quando usar: para consultar código ou vigência. Quando não usar: para buscar por descrição. | 5000 |
| `tuss_search` | `POST /v1/tuss_search` | `tuss_search` | Busca códigos TUSS por texto. Quando usar: para localizar procedimentos por descrição. Quando não usar: para validar XML. | 6000 |
| `sadt_missing` | `POST /v1/sadt_missing` | `tiss_sadt_missing` | Identifica campos obrigatórios SP/SADT ausentes. Quando usar: antes de renderizar uma guia. Quando não usar: para validar um lote. | 1000 |
| `sadt_catalog` | `POST /v1/sadt_catalog` | `tiss_sadt_catalog` | Retorna o catálogo SP/SADT. Quando usar: para conhecer campos e domínios. Quando não usar: para preencher uma guia sem dados. | 10000 |
| `rede` | `GET /v1/rede` | `tiss_rede` | Consulta as operadoras vinculadas a um CNPJ ou CNES. | 20000 |
| `operadora_rede` | `GET /v1/operadoras/{registro}/rede` | `operadora_rede` | Consulta os estabelecimentos vinculados a uma operadora. | 20000 |
| `operadora_perfil` | `GET /v1/operadoras/{registro_ans}` | `operadora_perfil` | Consulta o cadastro e a série semestral de glosa e pagamento de uma operadora na ANS. Quando usar: para conhecer uma operadora pelo registro ANS. Quando não usar: para buscar operadoras por nome. | 2500 |
| `sandbox_enviar_lote` | `POST /v1/sandbox/lotes` | `tiss_sandbox_enviar_lote` | Envia um lote à operadora simulada. Quando usar: para testar integração local. Quando não usar: para transmitir dados reais. | 2500 |
| `sandbox_demonstrativo` | `GET /v1/sandbox/lotes/{protocolo}/demonstrativo` | `tiss_sandbox_demonstrativo` | Gera o demonstrativo de um protocolo simulado. Quando usar: após enviar um lote. Quando não usar: com protocolo de outra operadora. | 5000 |

## Acesso

Sem chave, as operações `sandbox_*` e a lista de espera respondem. As demais exigem a chave
do login Voa em `Authorization: Bearer`. Não há limite diário.
Chave inválida ou expirada retorna `401`.
A chave vale 24 h e é renovada com o `refresh_token`.

| Rota HTTP | Descrição |
| --- | --- |
| `GET /v1/auth/login` | Inicia o login Voa. |
| `GET /v1/auth/callback` | Emite a chave e volta para `/chaves`. |
| `POST /v1/keys/refresh` | Troca o `refresh_token` por uma chave nova. |
| `GET /v1/limits` | Regras de acesso. |
| `GET /oauth/client.json` | Metadados do cliente OAuth. |

## Lista de espera

`POST /v1/lista-de-espera` recebe `modulo`, `email`, `empresa`, `volume_mensal`
e, para o extrator, `tipos_documento`. Retorna `202`, `422`, `429` ou `503`.
Nada é gravado; o pedido vai para a ferramenta de análise do produto.
