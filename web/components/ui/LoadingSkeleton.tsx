"use client";

import { Flex, Skeleton, theme } from "antd";

export function LoadingSkeleton() {
  const { token } = theme.useToken();
  return (
    <Flex vertical gap={token.marginLG} style={{ padding: token.paddingLG }}>
      <Skeleton active />
      <Skeleton active />
      <Skeleton active />
    </Flex>
  );
}
