"use client";

import { UserAddOutlined } from "@ant-design/icons";
import { Alert, App, Button, Card, Checkbox, Flex, Form, Input, Modal, Popconfirm, Result, Table, Tabs, Tag, theme, Tooltip, Typography } from "antd";
import type { TableColumnsType } from "antd";
import { useState } from "react";
import { FalhaDoPedido, pedir, useRecurso } from "@/lib/org/cliente";
import { dataHora } from "@/lib/org/formato";
import type { AreaDisponivel, Convite, Membro, Membros } from "@/lib/org/tipos";

const DESCRICAO_DA_AREA: Record<string, string> = {
  attendance: "Atendimento a pacientes e beneficiários.",
  scheduling: "Agenda e pedidos de horário.",
  finance: "Uso, custo estimado e cobrança.",
  administration: "Membros, chaves e configurações da organização.",
  clinical: "Revisões que vão para o profissional.",
  auditoria: "Aprova glosas e negativas propostas, sempre com justificativa escrita.",
};

function rotulosDasAreas(areas: string[], disponiveis: AreaDisponivel[]): string {
  const rotulos = new Map(disponiveis.map((area) => [area.value, area.label]));
  return disponiveis.filter((area) => areas.includes(area.value)).map((area) => area.label)
    .concat(areas.filter((area) => !rotulos.has(area)))
    .join(", ") || "Nenhuma";
}

function EditorDeAreas({
  membro,
  disponiveis,
  aoFechar,
  aoSalvar,
}: {
  membro: Membro;
  disponiveis: AreaDisponivel[];
  aoFechar: () => void;
  aoSalvar: () => void;
}) {
  const { token } = theme.useToken();
  const { message } = App.useApp();
  const [areas, setAreas] = useState(membro.areas);
  const [salvando, setSalvando] = useState(false);
  const travado = !membro.editable.areas.editable;

  async function salvar() {
    setSalvando(true);
    try {
      await pedir(`organization/members/${membro.id}/`, { method: "PATCH", body: { areas } });
      message.success(`${membro.name || membro.email} atualizado(a).`);
      aoSalvar();
    } catch (erro) {
      message.error(erro instanceof FalhaDoPedido ? erro.message : "Não foi possível salvar.");
      setSalvando(false);
    }
  }

  return (
    <Modal
      open
      title={`Áreas de ${membro.name || membro.email}`}
      okText="Salvar"
      cancelText="Cancelar"
      onOk={() => void salvar()}
      onCancel={aoFechar}
      okButtonProps={{ disabled: travado || areas.length === 0 || areas.join() === membro.areas.join(), loading: salvando }}
      destroyOnHidden
    >
      <Flex vertical gap={token.marginSM}>
        {travado && membro.editable.areas.reason && <Alert type="info" showIcon title={membro.editable.areas.reason} />}
        <Checkbox.Group
          value={areas}
          disabled={travado}
          onChange={(valores) => setAreas(disponiveis.map((area) => area.value).filter((valor) => valores.includes(valor)))}
        >
          <Flex vertical gap={token.marginXS}>
            {disponiveis.map((area) => (
              <Checkbox key={area.value} value={area.value}>
                <Flex vertical>
                  <Typography.Text>{area.label}</Typography.Text>
                  {DESCRICAO_DA_AREA[area.value] && (
                    <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>{DESCRICAO_DA_AREA[area.value]}</Typography.Text>
                  )}
                </Flex>
              </Checkbox>
            ))}
          </Flex>
        </Checkbox.Group>
        {areas.length === 0 && <Typography.Text type="danger">Escolha pelo menos uma Área.</Typography.Text>}
      </Flex>
    </Modal>
  );
}

function ListaDeMembros({ podeGerenciar, areasDaOrg }: { podeGerenciar: boolean; areasDaOrg: AreaDisponivel[] }) {
  const { token } = theme.useToken();
  const { message } = App.useApp();
  const membros = useRecurso<Membros>("organization/members/");
  const [editando, setEditando] = useState<Membro | null>(null);
  const disponiveis = membros.dados?.available_areas ?? areasDaOrg;

  async function remover(membro: Membro) {
    try {
      await pedir(`organization/members/${membro.id}/`, { method: "DELETE" });
      message.success(`${membro.name || membro.email} removido(a).`);
      membros.recarregar();
    } catch (erro) {
      message.error(erro instanceof FalhaDoPedido ? erro.message : "Não foi possível remover.");
    }
  }

  if (membros.erro) {
    return <Result status="error" title="Não foi possível carregar os membros." subTitle={membros.erro.message}
      extra={<Button onClick={membros.recarregar}>Tentar de novo</Button>} />;
  }

  const colunas: TableColumnsType<Membro> = [
    {
      title: "Membro",
      key: "membro",
      render: (_, membro) => (
        <Flex vertical>
          <Flex wrap align="center" gap={token.marginXXS}>
            <Typography.Text strong>{membro.name || membro.email}</Typography.Text>
            {membro.status === "sem_login" && <Tag>Sem login</Tag>}
          </Flex>
          {membro.name && <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>{membro.email}</Typography.Text>}
        </Flex>
      ),
    },
    { title: "Áreas", dataIndex: "areas", key: "areas", render: (areas: string[]) => rotulosDasAreas(areas, disponiveis) },
  ];
  if (podeGerenciar) {
    colunas.push({
      title: "Ações",
      key: "acoes",
      align: "right",
      render: (_, membro) => (
        <Flex justify="flex-end" gap={token.marginXS}>
          <Tooltip title={membro.editable.areas.editable ? undefined : membro.editable.areas.reason}>
            <Button type="link" onClick={() => setEditando(membro)}>Editar Áreas</Button>
          </Tooltip>
          {membro.removable.removable ? (
            <Popconfirm
              title={`Remover ${membro.name || membro.email}?`}
              description="A pessoa perde o acesso à organização na hora."
              okText="Remover"
              okButtonProps={{ danger: true }}
              cancelText="Cancelar"
              onConfirm={() => remover(membro)}
            >
              <Button type="link" danger>Remover</Button>
            </Popconfirm>
          ) : (
            <Tooltip title={membro.removable.reason}>
              <Button type="link" danger disabled>Remover</Button>
            </Tooltip>
          )}
        </Flex>
      ),
    });
  }

  return (
    <>
      <Table<Membro>
        aria-label="Membros da organização"
        rowKey="id"
        columns={colunas}
        dataSource={membros.dados?.members ?? []}
        loading={membros.carregando}
        pagination={false}
        scroll={{ x: 560 }}
        locale={{ emptyText: "Nenhum membro ainda." }}
      />
      {editando && (
        <EditorDeAreas
          key={editando.id}
          membro={editando}
          disponiveis={disponiveis}
          aoFechar={() => setEditando(null)}
          aoSalvar={() => {
            setEditando(null);
            membros.recarregar();
          }}
        />
      )}
    </>
  );
}

function ListaDeConvites({ versao }: { versao: number }) {
  const { message } = App.useApp();
  const convites = useRecurso<{ invites: Convite[] }>(`organization/invites/?v=${versao}`);

  async function agir(convite: Convite, acao: "resend" | "cancel") {
    try {
      await pedir(`organization/invites/${convite.id}/${acao}/`, { method: "POST", body: {} });
      message.success(acao === "resend" ? "Convite reenviado." : "Convite cancelado.");
      convites.recarregar();
    } catch (erro) {
      message.error(erro instanceof FalhaDoPedido ? erro.message : "Não foi possível concluir.");
    }
  }

  const colunas: TableColumnsType<Convite> = [
    { title: "E-mail", dataIndex: "email", key: "email" },
    { title: "Enviado por", dataIndex: "invited_by_name", key: "invited_by_name" },
    { title: "Enviado em", dataIndex: "created_at", key: "created_at", render: dataHora },
    { title: "Expira em", dataIndex: "expires_at", key: "expires_at", render: dataHora },
    {
      title: "Situação",
      dataIndex: "status",
      key: "status",
      render: (valor: string) => (valor === "expired" ? <Tag color="warning">Vencido</Tag> : <Tag color="processing">Aguardando</Tag>),
    },
    {
      title: "Ações",
      key: "acoes",
      align: "right",
      render: (_, convite) => (
        <>
          <Button type="link" onClick={() => void agir(convite, "resend")}>Reenviar</Button>
          <Popconfirm title="Cancelar o convite?" okText="Cancelar convite" cancelText="Voltar" onConfirm={() => agir(convite, "cancel")}>
            <Button type="link" danger>Cancelar</Button>
          </Popconfirm>
        </>
      ),
    },
  ];

  if (convites.erro) return <Alert type="error" showIcon title={convites.erro.message} />;
  return (
    <Table<Convite>
      aria-label="Convites enviados"
      rowKey="id"
      columns={colunas}
      dataSource={convites.dados?.invites ?? []}
      loading={convites.carregando}
      pagination={false}
      scroll={{ x: 760 }}
      locale={{ emptyText: "Nenhum convite aguardando resposta." }}
    />
  );
}

function ConvidarMembros({ aberto, aoFechar, aoConvidar }: { aberto: boolean; aoFechar: () => void; aoConvidar: () => void }) {
  const { notification } = App.useApp();
  const [form] = Form.useForm<{ emails: string }>();
  const [enviando, setEnviando] = useState(false);

  async function convidar({ emails: texto }: { emails: string }) {
    const emails = [...new Set(texto.split(/[\s,;]+/).map((email) => email.trim().toLowerCase()).filter(Boolean))];
    if (!emails.length) return;
    setEnviando(true);
    try {
      const resultado = await pedir<{ invites: Convite[]; already_member: string[] }>("organization/invites/", {
        method: "POST",
        body: { emails },
      });
      form.resetFields();
      aoFechar();
      if (resultado.invites.length) {
        notification.success({ title: resultado.invites.length === 1 ? "Convite enviado" : `${resultado.invites.length} convites enviados` });
        aoConvidar();
      }
      if (resultado.already_member.length) {
        notification.info({ title: "Já faziam parte", description: resultado.already_member.join(", ") });
      }
    } catch (erro) {
      notification.error({ title: "Erro ao convidar", description: erro instanceof FalhaDoPedido ? erro.message : undefined });
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Modal open={aberto} title="Convidar membros" footer={null} onCancel={aoFechar} destroyOnHidden>
      <Typography.Paragraph type="secondary">
        A pessoa entra depois de aceitar o convite. As Áreas se ajustam em Membros.
      </Typography.Paragraph>
      <Form form={form} layout="vertical" onFinish={(valores) => void convidar(valores)}>
        <Form.Item name="emails" label="E-mails" rules={[{ required: true, whitespace: true, message: "Informe ao menos um e-mail." }]}>
          <Input.TextArea placeholder="Um ou mais e-mails, separados por vírgula ou linha" autoSize={{ minRows: 2, maxRows: 4 }} />
        </Form.Item>
        <Button type="primary" htmlType="submit" block loading={enviando}>Convidar</Button>
      </Form>
    </Modal>
  );
}

export function MembersSection({ podeGerenciar, areasDaOrg }: { podeGerenciar: boolean; areasDaOrg: AreaDisponivel[] }) {
  const { token } = theme.useToken();
  const [aba, setAba] = useState("membros");
  const [convidando, setConvidando] = useState(false);
  const [versao, setVersao] = useState(0);
  const lista = <ListaDeMembros podeGerenciar={podeGerenciar} areasDaOrg={areasDaOrg} />;

  return (
    <Card
      title="Membros"
      extra={podeGerenciar && <Button type="primary" icon={<UserAddOutlined />} onClick={() => setConvidando(true)}>Convidar</Button>}
      styles={{ body: { display: "flex", flexDirection: "column", gap: token.margin } }}
    >
      {podeGerenciar ? (
        <Tabs
          activeKey={aba}
          onChange={setAba}
          items={[
            { key: "membros", label: "Membros", children: lista },
            { key: "convites", label: "Convites enviados", children: <ListaDeConvites versao={versao} /> },
          ]}
        />
      ) : (
        <>
          <Alert type="info" showIcon title="Só quem tem a Área Administração convida, edita e remove membros." />
          {lista}
        </>
      )}
      {podeGerenciar && (
        <ConvidarMembros
          aberto={convidando}
          aoFechar={() => setConvidando(false)}
          aoConvidar={() => {
            setVersao((valor) => valor + 1);
            setAba("convites");
          }}
        />
      )}
    </Card>
  );
}
