"use client";

import { Flex, Grid, theme } from "antd";
import type { ReactNode } from "react";
import { siteContentWidth } from "@/lib/site";

export function PageHeader({ children }: { children: ReactNode }) {
  const screens = Grid.useBreakpoint();
  const { token } = theme.useToken();

  return (
    <div
      style={{
        borderBottom: `${token.lineWidth}px ${token.lineType} ${token.colorSplit}`,
        paddingBlock: screens.md ? token.paddingLG : token.padding,
      }}
    >
      <Flex
        justify="space-between"
        align="center"
        gap={token.margin}
        style={{ maxWidth: siteContentWidth, marginInline: "auto" }}
      >
        {children}
      </Flex>
    </div>
  );
}
