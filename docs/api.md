# API HTTP e MCP

Orçamento aproximado: `ceil(tamanho UTF-8 do JSON / 4)` tokens.

| Operação | Rota HTTP | Tool MCP | Descrição | Orçamento |
| --- | --- | --- | --- | ---: |
| `validate` | `POST /v1/validate` | `tiss_validate` | Valida XML TISS ou lote em JSON. Quando usar: antes de gerar ou enviar um lote. Quando não usar: para corrigir achados sem aplicar o ciclo validar → tiss_apply_fixes → validar de novo. | 2500 |
| `parse_demonstrativo` | `POST /v1/parse_demonstrativo` | `tiss_parse_demonstrativo` | Lê decisões de um demonstrativo. Quando usar: para identificar pagamentos e glosas. Quando não usar: para validar lotes. | 1800 |
| `plan_reconciliation` | `POST /v1/plan_reconciliation` | `tiss_plan_reconciliation` | Propõe vínculos entre decisões e guias. Quando usar: após ler um demonstrativo. Quando não usar: para alterar guias. | 3000 |
| `tuss_lookup` | `POST /v1/tuss_lookup` | `tuss_lookup` | Busca um código TUSS exato. Quando usar: para consultar código ou vigência. Quando não usar: para buscar por descrição. | 5000 |
| `tuss_search` | `POST /v1/tuss_search` | `tuss_search` | Busca códigos TUSS por texto. Quando usar: para localizar procedimentos por descrição. Quando não usar: para validar XML. | 6000 |
| `sadt_missing` | `POST /v1/sadt_missing` | `tiss_sadt_missing` | Identifica campos obrigatórios SP/SADT ausentes. Quando usar: antes de renderizar uma guia. Quando não usar: para validar um lote. | 1000 |
| `sadt_catalog` | `POST /v1/sadt_catalog` | `tiss_sadt_catalog` | Retorna o catálogo SP/SADT. Quando usar: para conhecer campos e domínios. Quando não usar: para preencher uma guia sem dados. | 10000 |
| `rede` | `GET /v1/rede` | `tiss_rede` | Consulta as operadoras vinculadas a um CNPJ ou CNES. Quando usar: para identificar vínculos de um estabelecimento. Quando não usar: para buscar o cadastro geral; use operadora_lookup. | 20000 |
| `operadora_rede` | `GET /v1/operadoras/{registro}/rede` | `operadora_rede` | Consulta os estabelecimentos vinculados a uma operadora. Quando usar: para identificar unidades da rede por UF. Quando não usar: para buscar o cadastro geral; use operadora_lookup. | 20000 |
| `operadora_perfil` | `GET /v1/operadoras/{registro_ans}` | `operadora_perfil` | Consulta o cadastro e a série semestral de glosa e pagamento de uma operadora na ANS. Quando usar: para conhecer uma operadora pelo registro ANS. Quando não usar: para buscar operadoras por nome. | 2500 |
| `sandbox_enviar_lote` | `POST /v1/sandbox/lotes` | `tiss_sandbox_enviar_lote` | Envia um lote à operadora simulada. Quando usar: para testar integração local. Quando não usar: para transmitir dados reais. | 2500 |
| `sandbox_demonstrativo` | `GET /v1/sandbox/lotes/{protocolo}/demonstrativo` | `tiss_sandbox_demonstrativo` | Gera o demonstrativo de um protocolo simulado. Quando usar: após enviar um lote. Quando não usar: com protocolo de outra operadora. | 5000 |
| `build` | `POST /v1/build` | `tiss_build` | Gera o XML TISS 4.03.00 de um lote em JSON, com hash do epílogo. Consulte tiss://schemas/lote para o esquema estrutural. Quando usar: depois de validar o lote em JSON sem erros. Quando não usar: para corrigir achados; use tiss_apply_fixes. | 3000 |
| `hash` | `POST /v1/hash` | `tiss_hash` | Calcula o hash do epílogo de um XML TISS. Quando usar: para conferir a integridade do XML. Quando não usar: para validar o conteúdo; use tiss_validate. | 1000 |
| `audit` | `POST /v1/audit` | `tiss_audit` | Audita um lote JSON com regras locais e contexto da operadora. Quando usar: para identificar inconsistências administrativas. Quando não usar: para aplicar correções; use tiss_apply_fixes. | 1000 |
| `rejection_map` | `POST /v1/rejection-map` | `tiss_rejection_map` | Agrega achados por prestador e mês, sem expor dados das guias; CPF é pseudonimizado. Quando usar: para analisar rejeições por prestador. Quando não usar: para consultar guias individuais ou corrigir lotes. | 4000 |
| `apply_fixes` | `POST /v1/apply_fixes` | `tiss_apply_fixes` | Aplica correções JSON Patch de um relatório ao lote. Quando usar: depois de tiss_validate ou tiss_audit com achados corrigíveis. Quando não usar: para inventar dados ausentes; peça-os ao usuário. | 1500 |
| `glosa_explain` | `GET /v1/glosas/{codigo}` | `glosa_explain` | Explica um código da Tabela 38 da ANS. Quando usar: ao interpretar uma glosa recebida. Quando não usar: para validar ou corrigir o lote. | 1000 |
| `dominio` | `GET /v1/dominio` | `tiss_dominio` | Consulta tabelas e códigos de domínio TISS. Quando usar: para localizar um código ou termo de domínio. Quando não usar: para buscar procedimentos TUSS; use tuss_search. | 1000 |
| `operadora_lookup` | `GET /v1/operadoras` | `operadora_lookup` | Busca operadoras ativas pelo nome, registro, CNPJ ou localidade. Quando usar: para localizar uma operadora na base pública. Quando não usar: para consultar vínculos hospitalares; use tiss_rede. | 1000 |
| `referencia` | `GET /v1/referencia` | `tiss_referencia` | Consulta valores unitários de referência D-TISS da ANS por procedimento TUSS. Quando usar: para comparar valores informados por UF, modalidade, porte e semestre. Quando não usar: para glosa ou preço contratado de uma operadora; use as ferramentas de operadoras. | 1000 |
| `autorizacao_build` | `POST /v1/autorizacoes/build` | `tiss_autorizacao_build` | Gera XML TISS 4.03.00 para solicitação ou resposta de autorização SP/SADT. | 1500 |
| `autorizacao_parse` | `POST /v1/autorizacoes/parse` | `tiss_autorizacao_parse` | Interpreta solicitações e respostas de autorização SP/SADT. | 1500 |
| `autorizacao_check` | `POST /v1/autorizacoes/check` | `tiss_autorizacao_check` | Valida uma solicitação SP/SADT e retorna uma decisão explicável. | 2000 |
| `sandbox_autorizacao` | `POST /v1/sandbox/autorizacoes` | `tiss_sandbox_autorizacao` | Gera uma resposta SP/SADT sintética nos cenários disponíveis. | 1500 |
| `buscar_docs` | `GET /v1/docs` | `buscar_docs` | Busca trechos da documentação local da biblioteca. Quando usar: para encontrar instruções e referências da API. Quando não usar: para consultar dados clínicos ou códigos específicos. | 2000 |

## Acesso

Sem chave, respondem `sandbox_*` e a lista de espera. As demais exigem uma chave
`sk_tiss_` da organização em `Authorization: Bearer`, criada no painel
`/org`. Não há limite diário.
Chave inválida ou revogada retorna `401`; a revogação vale em até 60 s.
Chave sem o escopo da operação retorna `403`. Cada chamada com chave entra
no uso da organização, por operação e por chave.

| Escopo | Operações |
| --- | --- |
| `qualquer chave` | `tuss_lookup`, `tuss_search`, `rede`, `operadora_rede`, `operadora_perfil`, `glosa_explain`, `dominio`, `operadora_lookup`, `referencia`, `buscar_docs` |
| `tiss:accounts` | `parse_demonstrativo`, `plan_reconciliation` |
| `tiss:authorization` | `autorizacao_build`, `autorizacao_parse`, `autorizacao_check` |
| `tiss:build` | `build`, `apply_fixes` |
| `tiss:rules` | `audit`, `rejection_map` |
| `tiss:sandbox` | `sandbox_enviar_lote`, `sandbox_demonstrativo`, `sandbox_autorizacao` |
| `tiss:validate` | `validate`, `sadt_missing`, `sadt_catalog`, `hash` |

| Rota HTTP | Descrição |
| --- | --- |
| `GET /v1/limits` | Regras de acesso. |

## Lista de espera

`POST /v1/lista-de-espera` recebe `modulo`, `email`, `empresa`, `volume_mensal`
e, para o extrator, `tipos_documento`. Retorna `202`, `422`, `429` ou `503`.
Nada é gravado; o pedido vai para a ferramenta de análise do produto.
A rota é HTTP e não está disponível como ferramenta MCP.

## Prompts MCP

| Nome | Descrição | Argumentos |
| --- | --- | --- |
| `montar_lote` | Monta um lote TISS a partir de atendimentos e valida até convergir. | `atendimentos` (obrigatório), `operadora` (opcional) |
| `corrigir_lote_rejeitado` | Corrige um lote rejeitado pela operadora e revalida. | `lote` (obrigatório), `motivo` (opcional), `operadora` (opcional) |
| `tratar_demonstrativo` | Lê um demonstrativo, explica as glosas e propõe a conciliação. | `xml` (obrigatório), `guias` (opcional) |

## Resources MCP

| URI ou template | Descrição |
| --- | --- |
| `tiss://codigos` | Códigos estáveis de validação. |
| `tiss://sadt/catalogo` | Campos do catálogo SP/SADT. |
| `tiss://docs/readme` | Documentação principal. |
| `tiss://docs/api` | Operações HTTP e tools MCP. |
| `tiss://schemas/lote` | Schema JSON estrutural para lotes TISS. |
| `tiss://dominio/tabelas` | Tabelas de domínio TISS e suas fontes. |
| `tiss://operadoras` | Origem e quantidade de operadoras locais. |
| `tiss://regras/schema` | Esquema dos pacotes de regras por operadora. |
| `tiss://tuss/{tabela}/{pagina}` | Página local do catálogo TUSS. |
| `tiss://dominio/{tabela}` | Registros locais de uma tabela de domínio TISS. |
| `tiss://operadoras/{registro_ans}` | Cadastro e indicadores públicos de uma operadora. |
| `tiss://regras/{registro_ans}` | Pacote de regras publicado para uma operadora. |
