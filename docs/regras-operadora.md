# Regras por operadora

Pacotes JSON usam o contrato de [`rules.schema.json`](https://github.com/Voa-Health/tiss/blob/main/schemas/rules.schema.json).
Cada regra declara a origem, a severidade, o caminho e uma primitiva segura.
O caractere `*` percorre itens de listas. Padrões `padrao` usam RE2, casam o
valor inteiro (`fullmatch`) e são avaliados em tempo linear; lookaround e
backreferences não são aceitos. Cada pacote aceita até 500 regras, cada regex
tem até 200 caracteres e valores com mais de 10 000 caracteres falham sem
avaliar a regex.

Primitivas: `obrigatorio`, `padrao`, `valores`, `max_itens`,
`combinacao_proibida` e `exige_autorizacao`. Pacotes não executam código Python.

`exige_autorizacao` declara os códigos TUSS em `codigos`. Se um procedimento
executado corresponder a um desses códigos e a guia não tiver
`dados_autorizacao.senha`, a auditoria sinaliza a guia com glosa padrão 1818.

```mermaid
flowchart LR
    A[Lote] --> B[check]
    B --> C[Pacote JSON]
    C --> D[Achados com origem]
```

Regras oficiais exigem mantenedor do tipo `operadora` e fonte publicada.
Pacotes de exemplo devem usar dados sintéticos.

## Publicação pela operadora

Salve um pacote válido em `src/tiss/rules/NNNNNN.json`, com o registro ANS de seis dígitos
no nome, fonte e data em cada regra e `mantenedor` com `tipo: operadora` e `registro_ans`.
Envie a contribuição pelo GitHub; as verificações automáticas validam o pacote. Após
aprovação por responsável com e-mail no domínio cadastrado da operadora na ANS, as regras
recebem o selo Oficial.
Novas regras e ajustes são enviados pelo GitHub.
