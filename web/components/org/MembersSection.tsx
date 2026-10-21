"use client";

import {
  Button,
  Flex,
  Form,
  Grid,
  Input,
  message,
  Modal,
  Table,
  Tag,
  theme,
  Typography,
} from "antd";
import type { TableColumnsType } from "antd";
import { useState } from "react";
import type { Member } from "@/lib/org-mock";
import type { OrgRole } from "./types";

type MemberRow = Member & { convitePendente?: boolean };

export function MembersSection({
  initialMembers,
  role,
}: {
  initialMembers: Member[];
  role: OrgRole;
}) {
  const [members, setMembers] = useState<MemberRow[]>(initialMembers);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [form] = Form.useForm<{ email: string }>();
  const screens = Grid.useBreakpoint();
  const { token } = theme.useToken();

  function addInvite(values: { email: string }) {
    if (role !== "admin") return;
    setMembers((current) => [
      ...current,
      {
        id: `convite-${current.length + 1}`,
        nome: "Convite pendente",
        email: values.email,
        papel: "membro",
        convitePendente: true,
      },
    ]);
    setInviteOpen(false);
    form.resetFields();
    message.success("Convite adicionado à demonstração.");
  }

  const columns: TableColumnsType<MemberRow> = [
    {
      title: "Nome",
      dataIndex: "nome",
      key: "nome",
      render: (name: string, member) => member.convitePendente
        ? <Tag>Convite pendente</Tag>
        : name,
    },
    { title: "E-mail", dataIndex: "email", key: "email" },
    {
      title: "Papel",
      dataIndex: "papel",
      key: "papel",
      render: (value: Member["papel"]) => (
        <Tag color={value === "admin" ? "processing" : "default"}>
          {value === "admin" ? "Administrador" : "Membro"}
        </Tag>
      ),
    },
  ];

  return (
    <>
      <Flex vertical gap="var(--ant-margin)">
        <Flex wrap justify="space-between" align="center" gap="var(--ant-margin)">
          <Typography.Title level={3} style={{ margin: 0 }}>Membros</Typography.Title>
          {role === "admin" && (
            <Button type="primary" onClick={() => setInviteOpen(true)}>Convidar</Button>
          )}
        </Flex>
        {role === "membro" && (
          <Typography.Text
            type="secondary"
            style={{ color: token.colorTextSecondary }}
          >
            Somente administradores podem alterar.
          </Typography.Text>
        )}
        {!screens.md && (
          <Typography.Text
            type="secondary"
            style={{ color: token.colorTextSecondary }}
          >
            Deslize a tabela para ver outras colunas.
          </Typography.Text>
        )}
        <Table
          aria-label="Membros da organização"
          rowKey="id"
          columns={columns}
          dataSource={members}
          pagination={false}
          scroll={{ x: 520 }}
        />
      </Flex>
      <Modal
        title="Convidar membro"
        open={role === "admin" && inviteOpen}
        okText="Enviar convite"
        cancelText="Cancelar"
        onCancel={() => setInviteOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={addInvite}>
          <Form.Item
            name="email"
            label="E-mail"
            rules={[
              {
                required: true,
                message: (
                  <Typography.Text style={{ color: token.colorErrorTextActive }}>
                    Informe o e-mail.
                  </Typography.Text>
                ),
              },
              {
                type: "email",
                message: (
                  <Typography.Text style={{ color: token.colorErrorTextActive }}>
                    Informe um e-mail válido.
                  </Typography.Text>
                ),
              },
            ]}
          >
            <Input type="email" autoComplete="email" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
