"use client";

import { Alert, Button, Flex, Form, Input, theme } from "antd";
import { useState } from "react";
import { FalhaDoPedido, pedir } from "@/lib/org/cliente";

export function ReenviarEmail({ email }: { email?: string }) {
  const { token } = theme.useToken();
  const [estado, setEstado] = useState<{ tipo: "success" | "error"; texto: string } | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function reenviar(destino: string) {
    setEnviando(true);
    setEstado(null);
    try {
      await pedir("/api/org/reenviar", { method: "POST", body: { email: destino } });
      setEstado({ tipo: "success", texto: `Se houver conta pendente para ${destino}, um novo link chega em instantes.` });
    } catch (motivo) {
      setEstado({ tipo: "error", texto: motivo instanceof FalhaDoPedido ? motivo.message : "Não foi possível reenviar." });
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Flex vertical gap={token.marginSM}>
      {estado && <Alert type={estado.tipo} showIcon title={estado.texto} />}
      {email ? (
        <Button onClick={() => void reenviar(email)} loading={enviando}>Reenviar e-mail de confirmação</Button>
      ) : (
        <Form<{ email: string }> layout="inline" requiredMark={false} onFinish={({ email: valor }) => void reenviar(valor)}>
          <Form.Item name="email" rules={[{ required: true, type: "email", message: "Informe um e-mail válido." }]} style={{ flex: 1 }}>
            <Input type="email" autoComplete="email" placeholder="seu@email.com" aria-label="E-mail da conta" />
          </Form.Item>
          <Button htmlType="submit" loading={enviando}>Reenviar</Button>
        </Form>
      )}
    </Flex>
  );
}
