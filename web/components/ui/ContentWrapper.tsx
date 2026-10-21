"use client";

import { theme } from "antd";
import type { CSSProperties, ReactNode } from "react";
import { siteContentWidth } from "@/lib/site";

export function ContentWrapper({ children }: { children: ReactNode }) {
  const { token } = theme.useToken();
  return (
    <main
      style={
        {
          width: "100%",
          maxWidth: siteContentWidth,
          marginInline: "auto",
          padding: `${token.paddingLG}px ${token.padding}px`,
          minHeight: "60vh",
        } as CSSProperties
      }
    >
      {children}
    </main>
  );
}
