"use client";

import { Flex, theme } from "antd";
import type { ReactNode } from "react";

export function PageStack({ children }: { children: ReactNode }) {
  const { token } = theme.useToken();
  return (
    <Flex vertical gap={token.marginXXL}>
      {children}
    </Flex>
  );
}
