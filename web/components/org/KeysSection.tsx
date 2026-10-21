"use client";

import {
  Button,
  Card,
  Flex,
  Grid,
  message,
  Popconfirm,
  Table,
  Tag,
  theme,
  Typography,
} from "antd";
import type { TableColumnsType } from "antd";
import { useState } from "react";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDateTimeShort, keyLevelLabel } from "@/lib/site";
import type { OrgKey } from "@/lib/org-mock";
import type { OrgRole } from "./types";

export function KeysSection({
  initialKeys,
  role,
}: {
  initialKeys: OrgKey[];
  role: OrgRole;
}) {
  const [keys, setKeys] = useState(initialKeys);
  const screens = Grid.useBreakpoint();
  const { token } = theme.useToken();

  function revoke(id: string) {
    if (role !== "admin") return;
    setKeys((current) => current.filter((key) => key.id !== id));
    message.success("Chave revogada.");
  }

  const columns: TableColumnsType<OrgKey> = [
    {
      title: "Prefixo",
      dataIndex: "prefixo",
      key: "prefixo",
      width: 100,
      render: (prefix: string) => (
        <Typography.Text code style={{ whiteSpace: "nowrap" }}>{prefix}…</Typography.Text>
      ),
    },
    { title: "Membro", dataIndex: "membro_email", key: "membro_email", width: 165 },
    {
      title: "Nível",
      dataIndex: "nivel",
      key: "nivel",
      width: 130,
      render: (level: OrgKey["nivel"]) => <Tag>{keyLevelLabel(level)}</Tag>,
    },
    {
      title: "Validade",
      dataIndex: "expira_em",
      key: "expira_em",
      width: 155,
      onCell: () => ({ style: { whiteSpace: "nowrap" } }),
      render: (value: number) => formatDateTimeShort(value),
    },
    {
      title: "Último uso",
      dataIndex: "ultimo_uso",
      key: "ultimo_uso",
      width: 155,
      onCell: () => ({ style: { whiteSpace: "nowrap" } }),
      render: (value: number | null) =>
        value === null ? "Nunca usada" : formatDateTimeShort(value),
    },
  ];

  if (role === "admin") {
    columns.push({
      title: "Ação",
      key: "action",
      width: 100,
      render: (_, key) => (
        <Popconfirm
          title="Revogar esta chave?"
          description={
            <Typography.Text style={{ color: token.colorTextSecondary }}>
              A chave será removida desta demonstração.
            </Typography.Text>
          }
          okText="Revogar"
          cancelText="Cancelar"
          onConfirm={() => revoke(key.id)}
        >
          <Button
            type="link"
            danger
            style={{ color: token.colorErrorTextActive }}
          >
            Revogar
          </Button>
        </Popconfirm>
      ),
    });
  }

  return (
    <Flex vertical gap="var(--ant-margin)">
      <Flex wrap justify="space-between" align="center" gap="var(--ant-margin)">
        <Typography.Title level={3} style={{ margin: 0 }}>Chaves de acesso</Typography.Title>
        {keys.length > 0 && <Button type="primary" href="/entrar">Gerar chave</Button>}
      </Flex>
      {role === "membro" && (
        <Typography.Text
          type="secondary"
          style={{ color: token.colorTextSecondary }}
        >
          Somente administradores podem alterar.
        </Typography.Text>
      )}
      {keys.length ? (
        <>
          {!screens.md && (
            <Typography.Text
              type="secondary"
              style={{ color: token.colorTextSecondary }}
            >
              Deslize a tabela para ver outras colunas.
            </Typography.Text>
          )}
          <Card styles={{ body: { padding: 0 } }}>
            <Table
              aria-label="Chaves da organização"
              rowKey="id"
              columns={columns}
              dataSource={keys}
              pagination={false}
              scroll={{ x: role === "admin" ? 820 : 720 }}
            />
          </Card>
        </>
      ) : (
        <EmptyState
          title="Nenhuma chave ativa"
          description={
            <Typography.Text style={{ color: token.colorTextSecondary }}>
              Gere uma chave para continuar usando a API.
            </Typography.Text>
          }
          action={<Button type="primary" href="/entrar">Gerar chave</Button>}
        />
      )}
    </Flex>
  );
}
