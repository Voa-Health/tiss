"use client";

import { Flex, theme, Typography } from "antd";
import type { ReactNode } from "react";

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: ReactNode;
  action?: ReactNode;
}) {
  const { token } = theme.useToken();
  return (
    <Flex vertical align="center" gap={token.marginSM} style={{ padding: token.paddingXL, textAlign: "center" }}>
      <Typography.Title level={4} style={{ margin: 0 }}>
        {title}
      </Typography.Title>
      <Typography.Paragraph type="secondary" style={{ maxWidth: token.screenMD }}>
        {description}
      </Typography.Paragraph>
      {action}
    </Flex>
  );
}
