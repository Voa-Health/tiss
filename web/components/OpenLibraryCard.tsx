import { Card, Flex, Typography } from "antd";
import { CodeBlock } from "@/components/CodeBlock";
import { site } from "@/lib/site";

export function OpenLibraryCard() {
  return (
    <Card title="Comece com a biblioteca aberta">
      <Flex vertical gap={12}>
        <Typography.Paragraph>
          A biblioteca aberta já valida, gera e audita TISS offline.
        </Typography.Paragraph>
        <CodeBlock code={site.installCommand} />
      </Flex>
    </Card>
  );
}
