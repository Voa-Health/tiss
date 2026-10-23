# Gere da pasta web/demos: vhs cli.tape
Output ../public/demos/cli.gif
Source config.tape

Hide
Type "mkdir -p /tmp/tiss-demo && cp ../../src/tiss/examples/lote-valido.xml /tmp/tiss-demo/lote.xml && cp demonstrativo.xml /tmp/tiss-demo/ && cd /tmp/tiss-demo"
Enter
Type `export PS1='\[\e[1;35m\]$\[\e[0m\] ' && clear`
Enter
Sleep 500ms
Show

Type "# 1. Valide o lote e confira o hash antes de enviar"
Enter
Type "tiss validate lote.xml && tiss hash --check lote.xml"
Sleep 300ms
Enter
Wait@60s /\$$/
Sleep 2s
Type "# 2. Veja qual procedimento foi cobrado"
Enter
Type "grep -o 'codigoProcedimento>[0-9]\+' lote.xml | sort -u"
Sleep 300ms
Enter
Wait@60s /\$$/
Sleep 1500ms
Type "tiss tuss 10101012 | jq -r '.resultados[0].termo'"
Sleep 300ms
Enter
Wait@60s /\$$/
Sleep 2s
Type "# 3. A operadora glosou: pegue o código no demonstrativo"
Enter
Type "grep -o 'codigoGlosa>[0-9]\+' demonstrativo.xml"
Sleep 300ms
Enter
Wait@60s /\$$/
Sleep 1500ms
Type "tiss glosa 1801 | jq -r '.descricao, .orientacao.texto' | fold -sw 76"
Sleep 300ms
Enter
Wait@60s /\$$/
Sleep 6s
