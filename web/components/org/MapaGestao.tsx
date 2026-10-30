"use client";

import { Alert, App, Button, Card, Flex, Popconfirm, Typography, Upload } from "antd";
import { useState } from "react";
import { pedir } from "@/lib/org/cliente";
import { caminhoDoMapa, lerCadastro, prepararCadastro } from "@/lib/org/mapa";

export function MapaGestao({ orgId, ligada, recarregar }: { orgId: string; ligada: boolean; recarregar: () => void }) {
  const mapaDaOrg = caminhoDoMapa(orgId);
  const { modal, message } = App.useApp();
  const [segredo, setSegredo] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function buscarSegredo() {
    const valor = await pedir<{ secret: string }>(`${mapaDaOrg}secret/`);
    if (!/^[0-9a-f]{64}$/.test(valor.secret)) throw new Error("Segredo indisponível.");
    return valor.secret;
  }

  async function executar(acao: () => Promise<void>) {
    setOcupado(true); setErro(null);
    try { await acao(); }
    catch { setErro("Não foi possível concluir. Confira o arquivo ou tente de novo."); }
    finally { setOcupado(false); }
  }

  async function importar(arquivo: File) {
    if (arquivo.size > 2_000_000) { setErro("O arquivo deve ter até 2 MB."); return; }
    await executar(async () => {
      const itens = lerCadastro(await arquivo.text(), arquivo.name.toLowerCase().endsWith(".json"));
      const nomes = await prepararCadastro(itens, buscarSegredo);
      modal.confirm({
        title: "Substituir o cadastro inteiro?",
        content: `${nomes.length} nomes serão gravados. Os nomes atuais serão substituídos.`,
        okText: "Substituir cadastro", cancelText: "Cancelar",
        onOk: () => executar(async () => {
          await pedir(`${mapaDaOrg}provider/`, { method: "PUT", body: { items: nomes } });
          message.success("Cadastro atualizado."); recarregar();
        }),
      });
    });
  }

  return (
    <Card title="Gestão do mapa">
      <Flex vertical gap="middle">
        {erro && <Alert type="error" showIcon title={erro} />}
        <Typography.Text strong>Cadastro de nomes</Typography.Text>
        <Typography.Paragraph style={{ margin: 0 }}>
          CSV com cabeçalho <Typography.Text code>prestador,nome</Typography.Text> ou JSON
          com uma lista de objetos com esses campos. Cadastre nomes para código na operadora
          (codigo:…) e CPF; opcionalmente, informe CNPJ com ou sem máscara para sobrescrever
          o nome oficial do CNES. O CPF é pseudonimizado neste navegador antes do envio. Até 5000 nomes.
        </Typography.Paragraph>
        <Upload accept=".csv,.json" showUploadList={false} disabled={!ligada || ocupado}
          beforeUpload={(arquivo) => { void importar(arquivo); return false; }}>
          <Button loading={ocupado} disabled={!ligada}>Importar nomes (CSV ou JSON)</Button>
        </Upload>
        {!ligada && <Typography.Text type="secondary">Ligue a coleta para importar nomes ou consultar o segredo.</Typography.Text>}
        <Typography.Text strong>Uso pela CLI</Typography.Text>
        <Typography.Paragraph code copyable style={{ margin: 0 }}>
          TISS_KEY=sk_voa_… python -m tiss mapa &lt;pasta&gt; --enviar
        </Typography.Paragraph>
        <Typography.Text type="secondary">A CLI busca o segredo automaticamente. Guarde-o em local seguro se precisar configurar a pseudonimização manualmente.</Typography.Text>
        <Flex gap="small">
          <Button disabled={!ligada || ocupado} onClick={() => executar(async () => setSegredo(await buscarSegredo()))}>Mostrar segredo</Button>
          {segredo && <Button onClick={() => setSegredo(null)}>Ocultar segredo</Button>}
        </Flex>
        {segredo && <Alert type="warning" title="Segredo da organização" description={
          <Typography.Paragraph code copyable={{ text: segredo }} style={{ wordBreak: "break-all", margin: 0 }}>{segredo}</Typography.Paragraph>
        } />}
        <Typography.Text strong>Apagar dados</Typography.Text>
        <Typography.Text>Exclui todos os agregados, envios e nomes cadastrados. Não desliga a coleta.</Typography.Text>
        <Popconfirm title="Apagar todos os dados do mapa?" description="Esta ação não pode ser desfeita."
          okText="Apagar tudo" cancelText="Cancelar" okButtonProps={{ danger: true }}
          onConfirm={() => executar(async () => {
            await pedir(mapaDaOrg, { method: "DELETE" });
            setSegredo(null); recarregar(); message.success("Dados do mapa apagados.");
          })}>
          <Button danger disabled={ocupado}>Apagar tudo</Button>
        </Popconfirm>
      </Flex>
    </Card>
  );
}
