"use client";

import { CheckOutlined, CopyOutlined } from "@ant-design/icons";
import { Button, Flex, theme, Typography } from "antd";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { track } from "@/lib/analytics";

export function CodeBlock({ code, output = false }: { code: string; output?: boolean }) {
  const { token } = theme.useToken();
  const pathname = usePathname();
  const [copied, setCopied] = useState(false);
  const resetCopy = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (resetCopy.current) clearTimeout(resetCopy.current);
    },
    [],
  );

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code);
      track("tiss_copy_snippet", { pagina: pathname });
      setCopied(true);
      if (resetCopy.current) clearTimeout(resetCopy.current);
      resetCopy.current = setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <Flex vertical gap={token.marginXS} style={{ width: "100%", maxWidth: "100%", minWidth: 0 }}>
      {output && (
        <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
          Saída
        </Typography.Text>
      )}
      <Flex
        align="flex-start"
        gap={token.marginSM}
        style={{
          width: "100%",
          maxWidth: "100%",
          minWidth: 0,
          boxSizing: "border-box",
          padding: token.padding,
          background: output ? token.colorFillQuaternary : token.colorFillTertiary,
          borderRadius: token.borderRadius,
          overflow: "hidden",
        }}
      >
        <pre
          style={{
            flex: "1 1 auto",
            minWidth: 0,
            maxWidth: "100%",
            overflowX: "auto",
            whiteSpace: "pre",
            margin: 0,
            padding: 0,
            border: 0,
            borderRadius: 0,
            background: "transparent",
            fontFamily: token.fontFamilyCode,
            fontSize: token.fontSizeSM,
            color: output ? token.colorTextSecondary : token.colorText,
          }}
        >
          <code style={{ fontFamily: "inherit" }}>{code}</code>
        </pre>
        <Button
          size="small"
          type="text"
          icon={copied ? <CheckOutlined /> : <CopyOutlined />}
          aria-label={copied ? "Código copiado" : "Copiar código"}
          title={copied ? "Código copiado" : "Copiar código"}
          onClick={() => void copyCode()}
          style={{ flex: "none" }}
        />
      </Flex>
    </Flex>
  );
}
