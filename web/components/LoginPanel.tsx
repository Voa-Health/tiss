"use client";

import { Button, Card, Flex, theme, Typography } from "antd";
import { useState } from "react";
import { loginUrl } from "@/lib/site";

export function LoginPanel() {
  const { token } = theme.useToken();
  const [loading, setLoading] = useState(false);
  const simulated = process.env.NEXT_PUBLIC_LOGIN_SIMULADO === "1";

  function enter() {
    setLoading(true);
    window.location.assign(loginUrl());
  }

  return (
    <Card style={{ maxWidth: token.screenSM, marginInline: "auto" }}>
      <Flex vertical align="flex-start" gap={token.margin}>
        <Typography.Title level={2}>Entrar com Voa</Typography.Title>
        <Typography.Paragraph>
          Acesse com sua conta para receber uma chave de uso da API.
        </Typography.Paragraph>
        {simulated && <Typography.Text type="secondary">Modo simulado</Typography.Text>}
        <Button type="primary" size="large" loading={loading} onClick={enter}>
          Entrar com Voa
        </Button>
      </Flex>
    </Card>
  );
}
