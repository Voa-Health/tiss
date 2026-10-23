# Gere da pasta web/demos: vhs cli.tape
Output ../public/demos/cli.gif
Source config.tape

Hide
Type "mkdir -p /tmp/tiss-demo && cp ../../src/tiss/examples/lote-valido.xml /tmp/tiss-demo/lote.xml && cd /tmp/tiss-demo"
Enter
Type `export PS1='\[\e[1;35m\]$\[\e[0m\] ' && clear`
Enter
Sleep 500ms
Show

Type "tiss validate lote.xml"
Sleep 300ms
Enter
Wait@60s /\$$/
Sleep 2s
Type "tiss hash --check lote.xml"
Sleep 300ms
Enter
Wait@60s /\$$/
Sleep 2s
Type "tiss tuss 10101012 | jq '.resultados[0] | {codigo, termo}'"
Sleep 300ms
Enter
Wait@60s /\$$/
Sleep 3s
Type "tiss glosa 1801 | jq '{codigo, descricao, grupo}'"
Sleep 300ms
Enter
Wait@60s /\$$/
Sleep 5s
