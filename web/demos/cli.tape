# Gere da pasta web/demos: vhs cli.tape
Output ../public/demos/cli.gif
Source config.tape
Set FontSize 15

Hide
Type "cp lote-cli.xml /tmp/lote.xml && cd /tmp && rm -f corrigido.xml && clear"
Enter
Sleep 300ms
Show

Type "tiss validate lote.xml"
Enter
Wait@60s /\$$/
Sleep 4s
Type "tiss fix lote.xml -o corrigido.xml"
Enter
Wait@60s /\$$/
Sleep 3s
Type "sed -i 's/2026-10-32/2026-10-21/' corrigido.xml"
Enter
Wait@60s /\$$/
Sleep 1s
Type "tiss fix --write corrigido.xml && tiss validate corrigido.xml"
Enter
Wait@60s /\$$/
Sleep 3s
Hide
Type "clear"
Enter
Sleep 300ms
Show
Type "tiss glosa 1801 | jq '{codigo, descricao, orientacao: .orientacao.texto}'"
Enter
Wait@60s /\$$/
Sleep 5s
