"use client";

import { Alert, Button, Card, Flex, Form, Input, theme, Typography } from "antd";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { abrirDeNovo, FalhaDoPedido, pedir } from "@/lib/org/cliente";

type Campos = { email: string; senha: string };

export function OrgLogin({ aviso }: { aviso?: string }) {
  const { token } = theme.useToken();
  const [erro, setErro] = useState(aviso ?? "");
  const [enviando, setEnviando] = useState(false);

  async function entrar({ email, senha }: Campos) {
    setEnviando(true);
    setErro("");
    try {
      await pedir("/api/org/entrar", { method: "POST", body: { email, senha } });
      abrirDeNovo();
    } catch (motivo) {
      setErro(motivo instanceof FalhaDoPedido ? motivo.message : "Não foi possível entrar.");
      setEnviando(false);
    }
  }

  return (
    <Flex
      vertical
      align="center"
      justify="center"
      style={{ minHeight: "100vh", padding: token.paddingLG, background: token.colorBgLayout }}
    >
      <Card style={{ width: "100%", maxWidth: 440 }}>
        <Flex vertical gap={token.margin}>
          <Link href="/" aria-label="voa-tiss, página inicial" style={{ display: "inline-flex" }}>
            <Image src="/logo.svg" alt="Voa" width={88} height={24} priority />
          </Link>
          <Flex vertical gap={token.marginXXS}>
            <Typography.Title level={1} style={{ margin: 0, fontSize: token.fontSizeHeading3 }}>
              Organização voa-tiss
            </Typography.Title>
            <Typography.Text type="secondary">
              Entre com a conta Voa para gerenciar chaves, uso e membros da sua organização.
            </Typography.Text>
          </Flex>
          {erro && <Alert type="error" showIcon title={erro} />}
          <Form<Campos> layout="vertical" requiredMark={false} onFinish={(valores) => void entrar(valores)}>
            <Form.Item
              name="email"
              label="E-mail"
              rules={[{ required: true, type: "email", message: "Informe um e-mail válido." }]}
            >
              <Input type="email" autoComplete="username" />
            </Form.Item>
            <Form.Item name="senha" label="Senha" rules={[{ required: true, message: "Informe a senha." }]}>
              <Input.Password autoComplete="current-password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" block loading={enviando}>Entrar</Button>
          </Form>
          <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
            A senha vai direto para a Voa; este site não a guarda.
          </Typography.Text>
        </Flex>
      </Card>
    </Flex>
  );
}
