"use client";

import { AntdRegistry } from "@ant-design/nextjs-registry";
import { App, ConfigProvider } from "antd";
import type { ReactNode } from "react";
import { theme } from "@/tema";

export function ThemeProvider({ children }: { children: ReactNode }) {
  return (
    <AntdRegistry>
      <ConfigProvider theme={theme}>
        <App component={false}>{children}</App>
      </ConfigProvider>
    </AntdRegistry>
  );
}
