"use client";

import { Col, Flex, Row, Typography, theme } from "antd";
import Link from "next/link";
import { solutionGroups } from "@/lib/solutions";
import { site, siteContentWidth } from "@/lib/site";
import { track } from "@/lib/analytics";

export function SiteFooter() {
  const { token } = theme.useToken();
  const linkStyle = { color: token.colorTextSecondary } as const;

  return (
    <footer
      style={{
        borderTop: `${token.lineWidth}px ${token.lineType} ${token.colorBorderSecondary}`,
        paddingBlock: token.paddingXL,
        paddingInline: token.padding,
      }}
    >
      <Row
        gutter={[token.marginXL, token.marginLG]}
        style={{ maxWidth: siteContentWidth, marginInline: "auto" }}
      >
        {solutionGroups.map((group) => (
          <Col key={group.title} xs={24} sm={12} md={5}>
            <Flex vertical gap={token.marginXS}>
              <Typography.Text strong>{group.title}</Typography.Text>
              {group.links.map((item) => (
                <Link key={item.label} href={item.href} style={linkStyle}>
                  {item.label}
                </Link>
              ))}
            </Flex>
          </Col>
        ))}
        <Col xs={24} sm={12} md={4}>
          <Flex vertical gap={token.marginXS}>
            <Typography.Text strong>{site.name}</Typography.Text>
            <a
              href={site.github}
              style={linkStyle}
              onClick={() => track("tiss_cta_github", { local: "footer" })}
            >
              GitHub
            </a>
            <a href={site.pypi} style={linkStyle}>
              PyPI
            </a>
            <Link href="/termos" style={linkStyle}>
              Termos
            </Link>
          </Flex>
        </Col>
      </Row>
    </footer>
  );
}
