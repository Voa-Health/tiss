"use client";

import { CloseOutlined, RobotOutlined } from "@ant-design/icons";
import { Button, Empty, Flex, theme, Typography } from "antd";

export function PainelDoAssistente({ aoFechar }: { aoFechar: () => void }) {
  const { token } = theme.useToken();
  return (
    <Flex vertical gap={token.margin} style={{ height: "100%", padding: token.paddingLG }}>
      <Flex align="flex-start" justify="space-between" gap={token.marginSM}>
        <Flex vertical gap={token.marginXXS}>
          <Typography.Title level={2} style={{ margin: 0, fontSize: token.fontSizeHeading4 }}>
            Assistente de regras
          </Typography.Title>
          <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
            Descreva as regras de envio ou anexe o manual da operadora. O assistente propõe o
            pacote com a fonte de cada regra, valida e mostra o diff. Publicar é sempre uma
            decisão da Administração.
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
      <Flex flex={1} align="center" justify="center" style={{ minHeight: token.sizeXXL * 6 }}>
        <Empty
          image={<RobotOutlined style={{ fontSize: token.sizeXXL, color: token.colorTextQuaternary }} />}
          description="A conversa sobre as regras desta operadora aparece aqui."
        />
      </Flex>
    </Flex>
  );
}
