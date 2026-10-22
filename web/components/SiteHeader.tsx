"use client";

import { DownOutlined, MenuOutlined } from "@ant-design/icons";
import { Button, Drawer, Dropdown, Flex, Grid, theme, Typography } from "antd";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { moduleGroups } from "@/lib/modules";
import { loginSimulationEnabled, site, siteContentWidth } from "@/lib/site";

export function SiteHeader() {
  const screens = Grid.useBreakpoint();
  const { token } = theme.useToken();
  const [open, setOpen] = useState(false);
  const navigation = loginSimulationEnabled()
    ? [...site.navigation, { href: "/org", label: "Organização" }]
    : site.navigation;
  const links = navigation.map((item) => (
    <Link key={item.href} href={item.href} onClick={() => setOpen(false)}>
      {item.label}
    </Link>
  ));
  const moduleItems = moduleGroups.map((group) => ({
    type: "group" as const,
    key: group.title,
    label: group.title,
    children: group.links.map((item) => ({
      key: item.href,
      label: <Link href={item.href} onClick={() => setOpen(false)}>{item.label}</Link>,
    })),
  }));

  return (
    <header style={{ borderBottom: `${token.lineWidth}px ${token.lineType} ${token.colorBorderSecondary}` }}>
      <Flex
        align="center"
        justify="space-between"
        gap={token.margin}
        style={{ maxWidth: siteContentWidth, marginInline: "auto", padding: token.padding }}
      >
        <Link href="/" aria-label="voa-tiss, página inicial">
          <Image src="/logo.svg" alt="Voa" width={88} height={24} priority />
        </Link>
        {screens.md ? (
          <Flex align="center" gap={token.marginLG} className="site-nav">
            {links}
            <Dropdown menu={{ items: moduleItems }} trigger={["click"]}>
              <Button
                type="link"
                style={{
                  height: "auto",
                  paddingInline: 0,
                  fontSize: "inherit",
                  fontWeight: "inherit",
                }}
              >
                Módulos
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
                {moduleGroups.map((group) => (
                  <Flex key={group.title} vertical gap={token.marginSM}>
                    <Typography.Text strong>Módulos {group.title.toLowerCase()}</Typography.Text>
                    {group.links.map((item) => (
                      <Link key={item.href} href={item.href} onClick={() => setOpen(false)}>
                        {item.label}
                      </Link>
                    ))}
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
