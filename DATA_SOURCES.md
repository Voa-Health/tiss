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
  varia com a versão do PDA; `operators.json` 371,829 bytes.

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

## Hash do epílogo

O hash do epílogo é o MD5 do conteúdo da mensagem, sem o epílogo, codificado em
ISO-8859-1, conforme o padrão TISS da ANS.
