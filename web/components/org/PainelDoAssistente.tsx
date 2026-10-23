"use client";

import { CloseOutlined } from "@ant-design/icons";
import { Button, Flex, theme, Typography } from "antd";
import { Conversa } from "./Conversa";

export function PainelDoAssistente({
  aoFechar,
  podeDecidir,
}: {
  aoFechar: () => void;
  podeDecidir: boolean;
}) {
  const { token } = theme.useToken();
  return (
    <Flex vertical gap={token.margin} style={{ height: "100%", padding: token.paddingLG }}>
      <Flex align="flex-start" justify="space-between" gap={token.marginSM}>
        <Flex vertical gap={token.marginXXS}>
          <Typography.Title level={2} style={{ margin: 0, fontSize: token.fontSizeHeading4 }}>
            Assistente de regras
          </Typography.Title>
          <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
            O Assistente propõe alterações. A Auditoria decide; apenas a Administração publica.
          </Typography.Text>
        </Flex>
        <Button
          type="text"
          icon={<CloseOutlined />}
          aria-label="Fechar o assistente"
          onClick={aoFechar}
          data-fechar-assistente
        />
      </Flex>
      <Flex flex={1} vertical style={{ minHeight: 0 }}>
        <Conversa podeDecidir={podeDecidir} />
      </Flex>
    </Flex>
  );
}
