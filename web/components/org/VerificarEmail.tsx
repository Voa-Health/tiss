"use client";

import { Button, Card, Flex, Result, Spin, theme, Typography } from "antd";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { abrirDeNovo, FalhaDoPedido, pedir } from "@/lib/org/cliente";
import { ReenviarEmail } from "./ReenviarEmail";

export function VerificarEmail({ chave }: { chave: string }) {
  const { token } = theme.useToken();
  const [erro, setErro] = useState(chave ? "" : "Link de confirmação incompleto. Abra o link do e-mail de novo.");
  // A chave vale uma vez: o modo estrito do React montaria o efeito duas vezes.
  const enviada = useRef(false);

  useEffect(() => {
    if (!chave || enviada.current) return;
    enviada.current = true;
    pedir("/api/org/verificar", { method: "POST", body: { key: chave } })
      .then(() => abrirDeNovo("/org"))
      .catch((motivo: unknown) =>
        setErro(motivo instanceof FalhaDoPedido ? motivo.message : "Não foi possível confirmar o e-mail."),
      );
  }, [chave]);

  return (
    <Flex vertical align="center" justify="center" style={{ minHeight: "100vh", padding: token.paddingLG, background: token.colorBgLayout }}>
      <Card style={{ width: "100%", maxWidth: 480 }}>
        <Flex vertical gap={token.margin}>
          <Link href="/" aria-label="voa-tiss, página inicial" style={{ display: "inline-flex" }}>
            <Image src="/logo.svg" alt="Voa" width={88} height={24} priority />
          </Link>
          {erro ? (
            <>
              <Result status="warning" title="Não foi possível confirmar o e-mail" subTitle={erro} style={{ padding: 0 }}
                extra={<Button type="primary" href="/org">Entrar</Button>} />
              <Typography.Text type="secondary">Peça um novo link:</Typography.Text>
              <ReenviarEmail />
            </>
          ) : (
            <Flex vertical align="center" gap={token.margin} style={{ padding: token.paddingLG }}>
              <Spin size="large" />
              <Typography.Text>Confirmando o e-mail e abrindo sua conta…</Typography.Text>
            </Flex>
          )}
        </Flex>
      </Card>
    </Flex>
  );
}
