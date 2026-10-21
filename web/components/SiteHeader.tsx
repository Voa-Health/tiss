"use client";

import { MenuOutlined } from "@ant-design/icons";
import { Button, Drawer, Flex, Grid, theme } from "antd";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
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
          </Flex>
        ) : (
          <>
            <Button aria-label="Abrir menu" icon={<MenuOutlined />} onClick={() => setOpen(true)} />
            <Drawer title="Navegação" open={open} onClose={() => setOpen(false)}>
              <Flex vertical gap={token.marginLG}>
                {links}
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
