"use client";

import { Flex, theme } from "antd";
import Link from "next/link";
import { site } from "@/lib/site";

export function SiteFooter() {
  const { token } = theme.useToken();
  const linkStyle = { color: token.colorLink, textDecoration: "none" } as const;

  return (
    <footer
      style={{
        borderTop: `${token.lineWidth}px ${token.lineType} ${token.colorBorderSecondary}`,
        paddingBlock: token.paddingLG,
        paddingInline: token.padding,
      }}
    >
      <Flex justify="center" align="center" gap={token.margin} wrap>
        <Link href="/termos" style={linkStyle}>Termos</Link>
        <a href={site.github} style={linkStyle}>GitHub</a>
        <a href={site.pypi} style={linkStyle}>PyPI</a>
      </Flex>
    </footer>
  );
}
