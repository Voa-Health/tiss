"use client";

import { PlusOutlined } from "@ant-design/icons";
import { Alert, App, Button, Card, Flex, Form, Input, Modal, Popconfirm, Result, Segmented, Table, Tag, theme, Typography } from "antd";
import type { TableColumnsType } from "antd";
import { useState } from "react";
import { EmptyState } from "@/components/ui/EmptyState";
import { FalhaDoPedido, pedir, useRecurso } from "@/lib/org/cliente";
import { dataHora, inteiro } from "@/lib/org/formato";
import type { Chave, ChaveCriada } from "@/lib/org/tipos";
import { docsPageUrl } from "@/lib/site";

type NovaChave = { name: string; environment: Chave["environment"] };

const AMBIENTES = [
  { value: "production", label: "Produção" },
  { value: "sandbox", label: "Sandbox" },
] as const;

function SegredoUmaVez({ chave, aoFechar }: { chave: ChaveCriada | null; aoFechar: () => void }) {
  const { token } = theme.useToken();
  return (
    <Modal
      open={chave !== null}
      title="Chave criada"
      okText="Já guardei"
      onOk={aoFechar}
      onCancel={aoFechar}
      cancelButtonProps={{ style: { display: "none" } }}
      maskClosable={false}
      destroyOnHidden
    >
      <Flex vertical gap={token.margin}>
        <Alert type="warning" showIcon title="Guarde a chave agora: ela não aparece de novo." />
        <Typography.Paragraph copyable={{ text: chave?.secret ?? "" }} code style={{ wordBreak: "break-all", margin: 0 }}>
          {chave?.secret}
        </Typography.Paragraph>
        <Typography.Text type="secondary">
          Envie no cabeçalho <Typography.Text code>Authorization: Bearer</Typography.Text> da API e do MCP.
        </Typography.Text>
      </Flex>
    </Modal>
  );
}

export function KeysSection({ orgId, podeGerenciar }: { orgId: string; podeGerenciar: boolean }) {
  const { token } = theme.useToken();
  const { message } = App.useApp();
  const chaves = useRecurso<{ keys: Chave[] }>(`org/${orgId}/product-keys/`);
  const [form] = Form.useForm<NovaChave>();
  const [criando, setCriando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [criada, setCriada] = useState<ChaveCriada | null>(null);

  async function criar(valores: NovaChave) {
    setEnviando(true);
    try {
      const chave = await pedir<ChaveCriada>(`org/${orgId}/product-keys/`, { method: "POST", body: valores });
      setCriando(false);
      form.resetFields();
      setCriada(chave);
      chaves.recarregar();
    } catch (erro) {
      message.error(erro instanceof FalhaDoPedido ? erro.message : "Não foi possível criar a chave.");
    } finally {
      setEnviando(false);
    }
  }

  async function revogar(chave: Chave) {
    try {
      await pedir(`org/${orgId}/product-keys/${chave.id}/`, { method: "DELETE" });
      message.success(`Chave ${chave.name} revogada.`);
      chaves.recarregar();
    } catch (erro) {
      message.error(erro instanceof FalhaDoPedido ? erro.message : "Não foi possível revogar a chave.");
    }
  }

  const colunas: TableColumnsType<Chave> = [
    { title: "Nome", dataIndex: "name", key: "name" },
    {
      title: "Chave",
      dataIndex: "key_tip",
      key: "key_tip",
      render: (dica: string, chave) => <Typography.Text code style={{ whiteSpace: "nowrap" }}>{dica || `${chave.prefix}…`}</Typography.Text>,
    },
    {
      title: "Ambiente",
      dataIndex: "environment",
      key: "environment",
      render: (valor: Chave["environment"]) => (
        <Tag color={valor === "production" ? "processing" : "default"}>
          {AMBIENTES.find((item) => item.value === valor)?.label ?? valor}
        </Tag>
      ),
    },
    { title: "Usos", dataIndex: "usage_count", key: "usage_count", align: "right", render: (valor: number) => inteiro(valor) },
    {
      title: "Último uso",
      dataIndex: "last_used_at",
      key: "last_used_at",
      onCell: () => ({ style: { whiteSpace: "nowrap" } }),
      render: (valor: string | null) => (valor ? dataHora(valor) : "Nunca usada"),
    },
    {
      title: "Criada",
      key: "created",
      render: (_, chave) => (
        <Flex vertical>
          <Typography.Text style={{ whiteSpace: "nowrap" }}>{dataHora(chave.created_at)}</Typography.Text>
          {chave.created_by && <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>{chave.created_by}</Typography.Text>}
        </Flex>
      ),
    },
  ];
  if (podeGerenciar) {
    colunas.push({
      title: "Ação",
      key: "acao",
      align: "right",
      render: (_, chave) => (
        <Popconfirm
          title={`Revogar ${chave.name}?`}
          description="A chave para de funcionar na API e no MCP em até 1 minuto."
          okText="Revogar"
          okButtonProps={{ danger: true }}
          cancelText="Cancelar"
          onConfirm={() => revogar(chave)}
        >
          <Button type="link" danger>Revogar</Button>
        </Popconfirm>
      ),
    });
  }

  const botaoCriar = podeGerenciar && (
    <Button type="primary" icon={<PlusOutlined />} onClick={() => setCriando(true)}>Criar chave</Button>
  );

  let conteudo;
  if (chaves.erro) {
    conteudo = (
      <Result status="error" title="Não foi possível carregar as chaves." subTitle={chaves.erro.message}
        extra={<Button onClick={chaves.recarregar}>Tentar de novo</Button>} />
    );
  } else if (!chaves.carregando && chaves.dados?.keys.length === 0) {
    conteudo = (
      <EmptyState
        title="Nenhuma chave ativa"
        description="Crie uma chave para chamar a API e o MCP hospedados em nome da organização."
        action={botaoCriar || undefined}
      />
    );
  } else {
    conteudo = (
      <Table<Chave>
        aria-label="Chaves da organização"
        rowKey="id"
        columns={colunas}
        dataSource={chaves.dados?.keys ?? []}
        loading={chaves.carregando}
        pagination={false}
        scroll={{ x: 820 }}
      />
    );
  }

  return (
    <Card
      title="Chaves de acesso"
      extra={chaves.dados?.keys.length ? botaoCriar : null}
      styles={{ body: { display: "flex", flexDirection: "column", gap: token.margin } }}
    >
      {!podeGerenciar && (
        <Alert type="info" showIcon title="Só quem tem a Área Administração cria e revoga chaves." />
      )}
      {conteudo}
      <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
        Como usar a chave: <a href={docsPageUrl("api")}>referência da API</a>.
      </Typography.Text>
      <Modal
        open={criando}
        title="Criar chave"
        okText="Criar"
        cancelText="Cancelar"
        confirmLoading={enviando}
        onOk={() => form.submit()}
        onCancel={() => setCriando(false)}
        destroyOnHidden
      >
        <Form<NovaChave> form={form} layout="vertical" initialValues={{ environment: "production" }} onFinish={(valores) => void criar(valores)}>
          <Form.Item name="name" label="Nome" rules={[{ required: true, whitespace: true, message: "Dê um nome à chave." }]}>
            <Input placeholder="Ex.: integração do faturamento" maxLength={255} />
          </Form.Item>
          <Form.Item name="environment" label="Ambiente">
            <Segmented options={AMBIENTES.map((item) => ({ value: item.value, label: item.label }))} />
          </Form.Item>
        </Form>
      </Modal>
      <SegredoUmaVez chave={criada} aoFechar={() => setCriada(null)} />
    </Card>
  );
}
