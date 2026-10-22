"use client";

import { Flex, Typography, theme } from "antd";
import type { ReactNode } from "react";

export function Section({
  id,
  title,
  description,
  extra,
  level = 2,
  children,
}: {
  id: string;
  title: ReactNode;
  description?: ReactNode;
  extra?: ReactNode;
  level?: 1 | 2 | 3;
  children?: ReactNode;
}) {
  const { token } = theme.useToken();
  return (
    <section aria-labelledby={id}>
      <Flex vertical gap={token.marginLG}>
        <Flex vertical gap={token.marginXS} style={{ maxWidth: token.screenMD }}>
          <Typography.Title level={level} id={id} style={{ margin: 0 }}>
            {title}
          </Typography.Title>
          {description && (
            <Typography.Paragraph
              type="secondary"
              style={{ margin: 0, fontSize: level === 1 ? token.fontSizeLG : token.fontSize }}
            >
              {description}
            </Typography.Paragraph>
          )}
          {extra && <div style={{ marginBlockStart: token.marginSM }}>{extra}</div>}
        </Flex>
        {children}
      </Flex>
    </section>
  );
}
