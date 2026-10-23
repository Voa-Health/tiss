"use client";

import { DownOutlined, MenuOutlined } from "@ant-design/icons";
import { Button, Col, Drawer, Dropdown, Flex, Grid, Row, Tag, theme, Typography } from "antd";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { type SolutionLink, solutionGroups } from "@/lib/solutions";
import { site, siteContentWidth } from "@/lib/site";

export function SiteHeader() {
  const screens = Grid.useBreakpoint();
  const { token } = theme.useToken();
  const [open, setOpen] = useState(false);
  const navigation = site.navigation;
  const links = navigation.map((item) => (
    <Link key={item.href} href={item.href} onClick={() => setOpen(false)}>
      {item.label}
    </Link>
  ));
  const solutionLink = (item: SolutionLink) => (
    <Link
      key={item.label}
      href={item.href}
      onClick={() => setOpen(false)}
      className="solution-link"
      style={{ display: "block", padding: token.paddingXS, borderRadius: token.borderRadius }}
    >
      <Typography.Text style={{ display: "block" }}>{item.label}</Typography.Text>
      <Typography.Text type="secondary" style={{ display: "block", fontSize: token.fontSizeSM }}>
        {item.description}
      </Typography.Text>
      {item.tag && (
        <Tag
          color={item.tag === "Grátis" ? "green" : undefined}
          style={{ marginTop: token.marginXXS, marginInlineEnd: 0 }}
        >
          {item.tag}
        </Tag>
      )}
    </Link>
  );
  const solutionHeading = (group: (typeof solutionGroups)[number]) => (
    <Flex vertical style={{ paddingInline: token.paddingXS, marginBottom: token.marginXXS }}>
      <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
        {group.audience}
      </Typography.Text>
      <Typography.Text strong>{group.title}</Typography.Text>
    </Flex>
  );
  const solutionsPanel = (
    <div
      style={{
        width: 920,
        maxWidth: "calc(100vw - 32px)",
        padding: token.padding,
        background: token.colorBgElevated,
        borderRadius: token.borderRadiusLG,
        boxShadow: token.boxShadowSecondary,
      }}
    >
      <Row gutter={[token.margin, token.margin]}>
        {solutionGroups.map((group) => (
          <Col key={group.title} span={6}>
            {solutionHeading(group)}
            <Flex vertical gap={token.marginXXS}>
              {group.links.map(solutionLink)}
            </Flex>
          </Col>
        ))}
      </Row>
    </div>
  );

  return (
    <header style={{ borderBottom: `${token.lineWidth}px ${token.lineType} ${token.colorBorderSecondary}` }}>
      <Flex
        align="center"
        justify="space-between"
        gap={token.margin}
        style={{ maxWidth: siteContentWidth, marginInline: "auto", padding: token.padding }}
      >
        <Link href="/" aria-label="tiss, página inicial">
          <Image src="/logo.svg" alt="Voa" width={88} height={24} priority />
        </Link>
        {screens.md ? (
          <Flex align="center" gap={token.marginLG} className="site-nav">
            {links}
            <Dropdown popupRender={() => solutionsPanel} trigger={["click"]} placement="bottom">
              <Button
                type="link"
                style={{
                  height: "auto",
                  paddingInline: 0,
                  fontSize: "inherit",
                  fontWeight: "inherit",
                }}
              >
                Soluções
                <DownOutlined
                  style={{
                    marginInlineStart: token.marginXXS,
                    fontSize: token.fontSizeSM,
                  }}
                />
              </Button>
            </Dropdown>
          </Flex>
        ) : (
          <>
            <Button aria-label="Abrir menu" icon={<MenuOutlined />} onClick={() => setOpen(true)} />
            <Drawer title="Navegação" open={open} onClose={() => setOpen(false)}>
              <Flex vertical gap={token.marginLG}>
                {links}
                {solutionGroups.map((group) => (
                  <Flex key={group.title} vertical gap={token.marginXXS}>
                    {solutionHeading(group)}
                    {group.links.map(solutionLink)}
                  </Flex>
                ))}
                <Link href="/entrar" onClick={() => setOpen(false)}>Entrar</Link>
              </Flex>
            </Drawer>
          </>
        )}
        {screens.md && <Link href="/entrar">Entrar</Link>}
      </Flex>
    </header>
  );
}
