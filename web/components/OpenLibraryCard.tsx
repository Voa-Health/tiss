"use client";

import { Card, Flex, Typography, theme } from "antd";
import { CodeBlock } from "@/components/CodeBlock";
import { site } from "@/lib/site";

export function OpenLibraryCard() {
  const { token } = theme.useToken();
  return (
    <Card title="Comece com a biblioteca aberta" style={{ height: "100%" }}>
      <Flex vertical gap={token.marginSM}>
        <Typography.Paragraph style={{ margin: 0 }}>
          A biblioteca aberta já valida, gera e audita TISS offline.
        </Typography.Paragraph>
        <CodeBlock code={site.installCommand} />
      </Flex>
    </Card>
  );
}
