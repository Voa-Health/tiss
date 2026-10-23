# Fontes de dados

## XSD TISS 4.03.00

- Fonte ANS: https://www.gov.br/ans/pt-br/assuntos/prestadores/padrao-para-troca-de-informacao-de-saude-suplementar-2013-tiss/padrao-tiss-julho-2026
- Pacote de origem: https://www.gov.br/ans/pt-br/assuntos/prestadores/padrao-para-troca-de-informacao-de-saude-suplementar-2013-tiss/PadroTISSComunicao_202511.zip
- Data do pacote: 2025-11, conforme o nome do arquivo da ANS.
- Versão: 4.03.00; conjunto de 7 arquivos XSD e um manifesto de proveniência.
- SHA-256 do arquivo ZIP: `db8640e1c3b87085892f54f838bfcea9934439ff365798c8428559f88c13d62d`.
- Licença/atribuição: não informado na proveniência do pacote.
- Os hashes individuais dos XSDs estão registrados em `src/voa_tiss/_data/schemas/4.03.00/provenance.json`.

## Produtos e Prestadores Hospitalares

- Fonte ANS: https://dadosabertos.ans.gov.br/FTP/PDA/produtos_e_prestadores_hospitalares/produtos_e_prestadores_hospitalares.zip
- Página: https://dados.gov.br/dados/conjuntos-dados/produtos-e-prestadores-hospitalares
- Data de atualização: 2026-09-24.
- SHA-256 do ZIP: `e16da0d641d1213d32cb6b35a9aa07c192edcecdee162a49df52d1e92b5df3dc`.
- Contagens: 680 operadoras, 33.092 estabelecimentos, 932.625 vínculos; 31.893 estabelecimentos com CNPJ.
- Licença/atribuição: `CC BY, atribuição à ANS`.

## TUSS — tabelas 18, 19, 20 e 22

- Fonte: ANS, Terminologia Unificada da Saúde Suplementar (TUSS), dados abertos:
  https://dadosabertos.ans.gov.br/FTP/PDA/terminologia_unificada_saude_suplementar_TUSS-049/
  (arquivo `pda-049-tuss.zip`).
- Data da extração: 2026-10-09 (data do commit do conjunto de dados usado como origem).
- Registros: 68.022 no conjunto distribuído; tabela 18: 3.597; tabela 19: 45.889;
  tabela 20: 12.572; tabela 22: 5.964.
- SHA-256 do arquivo distribuído: `edc1a978227f46eb33eb228877e51f3042d1863bf0f7e31f3f0889384ee3ab3d`.
- Licença: dados abertos da ANS, CC BY-ND; redistribuição verbatim com atribuição. As tabelas são distribuídas sem alteração.
- Atribuição: ANS — Terminologia Unificada da Saúde Suplementar (TUSS).
- A geração local usa `uv run python scripts/manutencao.py tuss --table ID=CAMINHO.csv`.

Quando a fonte não publica uma licença ou metadado específico, o valor é indicado como
“não informado”; não se presume autorização além dos termos publicados pela fonte.

## Tabela 38 e domínios TISS

- Tabela 38: ANS, *Componente de Representação de Conceitos em Saúde*, versão 202609,
  arquivo `TUSS - Demais terminologias - VERSÃO 202609.xlsx` no ZIP:
  https://www.ans.gov.br/arquivos/extras/tiss/Padrao_TISS_Representacao_de_Conceitos_em_Saude_202609.zip
- SHA-256 do ZIP utilizado: `7f3d7a9794a8929fddd6f13af26dd9496087bf8b8670f275bd7ecd9a2f64172d`.
- Tabela 38: 470 termos; licença como publicada: não informado.
- A planilha não publica um campo de grupo. As orientações locais agrupam códigos
  pelo prefixo de dois dígitos; essa classificação não é atribuída à ANS.
- Orientações de recurso por grupo foram escritas pela Voa, em caráter procedural e sem
  afirmações clínicas.
- Domínios TISS: tabelas PDA do arquivo `pda-049-tuss.zip`; excluídas TUSS 18/19/20/22
  e tabela 64. CADOP: `Relatorio_cadop.csv` de dados abertos ANS
  (https://dados.gov.br/dados/conjuntos-dados/operadoras-de-planos-de-saude-ativas);
  licença: CC BY, atribuição à ANS.
- Tamanhos distribuídos: `glosas.json` 285,670 bytes; domínio após incluir Tabela 38
  varia com a versão do PDA; `healthplans.json` 371,829 bytes.

## Painel de Indicadores de Glosa

- Fonte: ANS, Painel de Indicadores de Glosa:
  https://dados.gov.br/dados/conjuntos-dados/painel-de-indicadores-de-glosa
- Arquivos: os cinco CSVs `pda-057-painel_de_glosas-*.csv` de
  https://dadosabertos.ans.gov.br/FTP/PDA/painel_de_glosas-057/dados/; URL e SHA-256 de cada
  um ficam em `src/voa_tiss/operadoras/_data/indicadores.json`.
- Data de carga (`DT_CARGA`): 2026-07-20; semestres de 2019-01 a 2025-02.
- Registros: 853 operadoras ativas no CADOP; as que não estão no CADOP ficam de fora.
- Licença: CC BY, atribuição à ANS.
- Valor ausente ou "-" vira `null`. O semestre fica inconsistente quando o valor é `null` ou
  passa de três vezes a mediana dos semestres anteriores da mesma operadora e indicador, com
  salto de ao menos 10 pontos percentuais (30 dias no tempo médio de pagamento) sobre essa
  mediana; o valor é mantido. Essa marcação é da Voa, não da ANS.
- Tamanho distribuído: `indicadores.json` 490,139 bytes.
- A geração local usa `uv run python scripts/manutencao.py ans-glosa`.

## Valores unitários D-TISS por TUSS

- Fonte: ANS, dados abertos do Padrão TISS:
  https://dadosabertos.ans.gov.br/FTP/PDA/TISS/
- Recorte: semestre `2025-2`, de julho a dezembro de 2025, 27 UFs e as categorias
  ambulatorial e hospitalar. Foram lidos 648 arquivos ZIP CONS e DET; os arquivos REM
  não foram usados.
- Data de referência dos arquivos: 2026-05-23.
- Licença e atribuição: CC BY 4.0, atribuição à ANS.
- SHA-256 combinado dos 648 arquivos ZIP: `46bb6dc9f2f13bfbc2005bd29141f723ee19eec1229c179ee1009acc67305541`.
- Contagens: 397.561.447 eventos, 889.926.454 itens lidos, 788.878.578 itens usados,
  466.933 células publicadas, 1.196.043 células suprimidas e 44.071 blocos de pagamento
  direto publicados.
- Carga: 1 h 26 min 04 s, com oito trabalhadores; pico de memória residente de 9.502.872
  KiB (aproximadamente 9,06 GiB). Foram baixados 11.359.335.950 bytes.
- Arquivo SQLite: `dist/referencia/referencia-dtiss.sqlite`, 40.095.744 bytes;
  SHA-256 `34bf6d5a72e65157f5782814b9075094bacdfdf6915af35dc588b2c022a59411`.
- Arquivo distribuível: `dist/referencia/referencia-dtiss.sqlite.gz`, 8.579.298 bytes;
  SHA-256 `723917c24cedfd7eb370d3ea2f76a5d9abc401cb89391decfd661d55d510ff14`.
- URL prevista no manifesto: https://voa-tiss-dados.s3.sa-east-1.amazonaws.com/publico/referencia/2026-05-23/referencia-dtiss.sqlite.gz.
  O arquivo foi mantido localmente e não foi enviado ao S3.
- Cada valor unitário é o valor total informado dividido pela quantidade, arredondado
  para centavos por `ROUND_HALF_UP`. As células usam código TUSS, tabela, UF, modalidade,
  porte e semestre; a UF vem de `UF_PRESTADOR` no CONS, com fallback para a UF do arquivo
  quando ausente. Cada item também contribui para as marginais de modalidade ou porte,
  sem agregação nacional. `pacote_pct` usa todos os itens antes da exclusão de atípicos.
- A mediana, p25 e p75 usam quantis tipo 7 sobre a distribuição ponderada após as
  exclusões. Só são publicadas células com pelo menos 30 itens. O limite para exclusão
  de valores atípicos é Q3 + 3×IQR, calculado sobre a célula completa; `n` é anterior à
  exclusão e a fração excluída é informada.
- Os valores pagos consideram somente pagamentos positivos feitos diretamente ao
  fornecedor, não o total pago pela operadora; têm contagem mínima e exclusão de atípicos
  próprias.
- Aviso para 2025: “A ANS informa valores atípicos em VL_ITEM_EVENTO_INFORMADO em 2025;
  os itens acima de Q3 + 3×IQR de cada célula foram excluídos e a fração excluída é
  publicada.”

## Hash do epílogo

O hash do epílogo é o MD5 do conteúdo da mensagem, sem o epílogo, codificado em
ISO-8859-1, conforme o padrão TISS da ANS.
