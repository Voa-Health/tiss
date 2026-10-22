"use client";

import { Flex, theme } from "antd";
import Link from "next/link";
import { site } from "@/lib/site";
import { track } from "@/lib/analytics";

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
        {site.modules.map((item) => (
          <Link key={item.href} href={item.href} style={linkStyle}>{item.label}</Link>
        ))}
        <a href={site.github} style={linkStyle} onClick={() => track("tiss_cta_github", { local: "footer" })}>GitHub</a>
        <a href={site.pypi} style={linkStyle}>PyPI</a>
      </Flex>
    </footer>
  );
}
