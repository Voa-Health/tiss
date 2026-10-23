"use client";

import { Alert, App, Button, Card, Checkbox, Empty, Flex, Form, Input, Popconfirm, Select, Skeleton, Table, Tag, Typography } from "antd";
import type { TableColumnsType } from "antd";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { pedir, useRecurso } from "@/lib/org/cliente";
import { brl, dataHora } from "@/lib/org/formato";
import { CAMINHO_DO_MAPA, matrizDoMapa, rotuloDoPrestador } from "@/lib/org/mapa";
import type { CelulaDoMapa, LinhaDaMatriz, MapaDeRejeicao } from "@/lib/org/mapa";
import type { EstadoDaOrg } from "@/lib/org/tipos";
import { MapaGestao } from "./MapaGestao";

function Celula({ valor }: { valor?: CelulaDoMapa }) {
  return valor ? <Flex vertical><Typography.Text>{valor.guias} guias com achado</Typography.Text><Typography.Text type="secondary">{brl(valor.centavos / 100)}</Typography.Text></Flex> : <Typography.Text type="secondary">—</Typography.Text>;
}

function MapaConteudo({ org }: { org: EstadoDaOrg }) {
  const router = useRouter(), params = useSearchParams();
  const admin = org.is_admin || org.my_areas.includes("administration");
  const podeVer = org.rejection_map?.eligible && org.type === "pay" && (admin || org.my_areas.includes("auditoria"));
  const filtros = new URLSearchParams();
  for (const campo of ["prestador", "rule_id", "mes_de", "mes_ate"]) {
    const valor = params.get(campo); if (valor) filtros.set(campo, valor);
  }
  const mapa = useRecurso<MapaDeRejeicao>(podeVer ? `${CAMINHO_DO_MAPA}?${filtros}` : null);
  const [aceito, setAceito] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function ligar(ligada: boolean) {
    setOcupado(true); setErro(null);
    try {
      await pedir(`${CAMINHO_DO_MAPA}${ligada ? "enable" : "disable"}/`, {
        method: "POST",
        ...(ligada ? { body: { accept_terms: true, terms_version: mapa.dados?.terms.current_version } } : {}),
      });
      setAceito(false); mapa.recarregar();
    } catch { setErro("Não foi possível alterar a coleta. Atualize a página e tente novamente."); }
    finally { setOcupado(false); }
  }

  function filtrar(valores: Record<string, string | undefined>) {
    if (valores.mes_de && valores.mes_ate && valores.mes_de > valores.mes_ate) {
      setErro("O mês inicial deve ser anterior ou igual ao mês final."); return;
    }
    setErro(null);
    const novos = new URLSearchParams(params.toString());
    for (const campo of ["prestador", "rule_id", "mes_de", "mes_ate"]) {
      novos.delete(campo); if (valores[campo]) novos.set(campo, valores[campo]);
    }
    router.replace(`/org?${novos}`, { scroll: false });
  }

  if (!podeVer) return <Alert type="warning" title="Mapa indisponível para esta organização ou Área." />;
  if (mapa.carregando) return <Skeleton active />;
  if (mapa.erro || !mapa.dados) return <Alert type="error" showIcon title="Não foi possível carregar o mapa."
    description={mapa.erro?.message} action={<Button onClick={mapa.recarregar}>Tentar de novo</Button>} />;
  const dados = mapa.dados;
  const matriz = matrizDoMapa(dados.linhas);
  const colunas: TableColumnsType<LinhaDaMatriz> = [
    { title: "Prestador", key: "prestador", fixed: "left", width: 260, render: (_, linha) => <Flex vertical>
      <Typography.Text strong>{rotuloDoPrestador(linha.prestador)}</Typography.Text>
      {linha.prestador.nome_origem && <Typography.Text type="secondary" style={{ fontSize: 12 }}>Nome: {linha.prestador.nome_origem === "cnes" ? "CNES" : linha.prestador.nome_origem}</Typography.Text>}
    </Flex> },
    ...matriz.meses.map((mes) => ({ title: mes, key: mes, width: 190, render: (_: unknown, linha: LinhaDaMatriz) => <Celula valor={linha.meses[mes]} /> })),
    { title: "Total", key: "total", width: 190, render: (_, linha) => <Celula valor={linha.total} /> },
  ];

  return <Flex vertical gap="middle">
    <Card title={<Flex align="center" gap="small">Coleta do mapa <Tag color={dados.enabled ? "green" : undefined}>{dados.enabled ? "Ligada" : "Desligada"}</Tag></Flex>}>
      <Flex vertical gap="middle">
        {erro && <Alert type="error" showIcon title={erro} />}
        <Typography.Paragraph style={{ margin: 0 }}>Somente agregados por prestador, código, regra e mês. CPF pseudonimizado com HMAC por organização; CNPJ em claro. Retenção de 24 meses. Você pode apagar os dados aqui.</Typography.Paragraph>
        <Typography.Link href="/termos#mapa-de-rejeicao" target="_blank" rel="noreferrer">Termo do mapa de rejeição — versão {dados.terms.current_version}</Typography.Link>
        {dados.terms.accepted_at && <Typography.Text type="secondary">Aceite da versão {dados.terms.version} em {dataHora(dados.terms.accepted_at)}</Typography.Text>}
        {admin ? dados.enabled ? <Popconfirm title="Desligar a coleta?" description="Os dados já coletados serão mantidos." okText="Desligar" cancelText="Cancelar" onConfirm={() => ligar(false)}>
          <Button loading={ocupado}>Desligar</Button>
        </Popconfirm> : <>
          <Checkbox checked={aceito} onChange={(evento) => setAceito(evento.target.checked)}>Li e aceito o termo do mapa de rejeição, versão {dados.terms.current_version}.</Checkbox>
          <Button type="primary" disabled={!aceito} loading={ocupado} onClick={() => ligar(true)}>Ligar</Button>
        </> : <Typography.Text type="secondary">Somente Administração pode alterar a coleta e gerenciar os dados.</Typography.Text>}
      </Flex>
    </Card>
    <Card title="Achados por prestador e mês">
      <Form layout="vertical" onFinish={filtrar} initialValues={Object.fromEntries(filtros)} key={filtros.toString()}>
        <Flex gap="middle" wrap align="end">
          <Form.Item name="prestador" label="Prestador" style={{ minWidth: 240 }}><Select allowClear placeholder="Todos os prestadores" options={dados.prestadores.map((prestador) => ({ value: prestador.id, label: rotuloDoPrestador(prestador) }))} /></Form.Item>
          <Form.Item name="rule_id" label="Regra" style={{ minWidth: 180 }}><Select allowClear placeholder="Todas as regras" options={dados.rule_ids.filter((id): id is string => id !== null).map((id) => ({ value: id, label: id }))} /></Form.Item>
          <Form.Item name="mes_de" label="Mês inicial"><Input type="month" /></Form.Item>
          <Form.Item name="mes_ate" label="Mês final"><Input type="month" /></Form.Item>
          <Form.Item><Button htmlType="submit">Aplicar filtros</Button></Form.Item>
          <Form.Item><Button onClick={() => filtrar({})}>Limpar filtros</Button></Form.Item>
        </Flex>
      </Form>
      {matriz.linhas.length ? <Table rowKey={(linha) => linha.prestador.id} columns={colunas} dataSource={matriz.linhas} pagination={{ pageSize: 20 }} scroll={{ x: 260 + 190 * (matriz.meses.length + 1) }} /> : <Empty description="Nenhum achado para os filtros selecionados." />}
    </Card>
    {admin && <MapaGestao key={String(dados.enabled)} ligada={dados.enabled} recarregar={mapa.recarregar} />}
  </Flex>;
}

export function MapaSection({ org }: { org: EstadoDaOrg }) {
  return <App><MapaConteudo org={org} /></App>;
}
