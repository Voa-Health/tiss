"use client";

import { DownOutlined, LogoutOutlined, PlusOutlined, RobotOutlined, SwapOutlined } from "@ant-design/icons";
import { App, Button, Drawer, Dropdown, Flex, Grid, Tag, theme, Typography } from "antd";
import type { MenuProps } from "antd";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { abrirDeNovo, FalhaDoPedido, pedir } from "@/lib/org/cliente";
import type { EstadoDaOrg } from "@/lib/org/tipos";
import { site } from "@/lib/site";
import { PainelDoAssistente } from "./PainelDoAssistente";
import { hrefDaOrg, ROTULO_DO_TIPO, secoesDaOrg, secoesVisiveisDaOrg, type SecaoDaOrg } from "./secoes";

const LARGURA = 1440;
const LARGURA_DO_PAINEL = 416;

export async function sair() {
  await pedir("/api/org/sair", { method: "POST", body: {} }).catch(() => null);
  abrirDeNovo();
}

function SeletorDeOrg({ org, outras }: { org: EstadoDaOrg; outras: EstadoDaOrg[] }) {
  const { token } = theme.useToken();
  const { message } = App.useApp();

  async function trocar(id: string) {
    try {
      await pedir("/api/org/trocar", { method: "POST", body: { organization_id: id } });
      abrirDeNovo();
    } catch (erro) {
      message.error(erro instanceof FalhaDoPedido ? erro.message : "Não foi possível trocar de organização.");
    }
  }

  const items: MenuProps["items"] = [
    ...outras.map((item) => ({ key: item.id, label: item.name, icon: <SwapOutlined /> })),
    ...(outras.length ? [{ type: "divider" as const }] : []),
    { key: "nova", label: "Nova organização", icon: <PlusOutlined /> },
  ];

  return (
    <Dropdown
      trigger={["click"]}
      menu={{
        items,
        onClick: ({ key }) => (key === "nova" ? abrirDeNovo("/org?nova=1") : void trocar(key)),
      }}
    >
      <Button aria-label={`Organização atual: ${org.name}. Trocar de organização`}>
        <Flex align="center" gap={token.marginXS} style={{ minWidth: 0 }}>
          <Typography.Text strong ellipsis style={{ maxWidth: 220 }}>{org.name}</Typography.Text>
          <Tag style={{ marginInlineEnd: 0 }}>{ROTULO_DO_TIPO[org.type] ?? org.type_display}</Tag>
          <DownOutlined style={{ fontSize: token.fontSizeSM }} />
        </Flex>
      </Button>
    </Dropdown>
  );
}

export function OrgCasca({
  org,
  outras,
  secao,
  painelAberto,
  children,
}: {
  org: EstadoDaOrg;
  outras: EstadoDaOrg[];
  secao: SecaoDaOrg;
  painelAberto: boolean;
  children: ReactNode;
}) {
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const router = useRouter();
  const operadora = org.type === "pay";
  const painel = operadora && painelAberto;
  const secoes = secoesVisiveisDaOrg(org);
  const atual = secoes.find((item) => item.key === secao) ?? secoesDaOrg[0];
  const alternarPainel = (aberto: boolean) => router.replace(hrefDaOrg(secao, aberto), { scroll: false });
  const borda = `${token.lineWidth}px ${token.lineType} ${token.colorBorderSecondary}`;

  return (
    <div style={{ minHeight: "100vh", background: token.colorBgLayout }}>
      <a className="org-skip" href="#conteudo-da-org">Ir para o conteúdo</a>
      <header style={{ background: token.colorBgContainer, borderBottom: borda }}>
        <Flex
          wrap
          align="center"
          justify="space-between"
          gap={token.margin}
          style={{ maxWidth: LARGURA, margin: "0 auto", padding: `${token.paddingSM}px ${token.paddingLG}px` }}
        >
          <Flex align="center" gap={token.margin}>
            <Link href="/" aria-label="tiss, página inicial" style={{ display: "inline-flex" }}>
              <Image src="/logo.svg" alt="Voa" width={88} height={24} priority />
            </Link>
            <Typography.Text
              type="secondary"
              style={{ borderInlineStart: borda, paddingInlineStart: token.margin }}
            >
              Organização
            </Typography.Text>
          </Flex>
          <Flex wrap align="center" gap={token.marginSM}>
            <SeletorDeOrg org={org} outras={outras} />
            {operadora && (
              <Button
                type={painel ? "primary" : "default"}
                icon={<RobotOutlined />}
                aria-expanded={painel}
                aria-controls="painel-do-assistente"
                onClick={() => alternarPainel(!painel)}
              >
                Assistente
              </Button>
            )}
            <Button icon={<LogoutOutlined />} onClick={() => void sair()}>Sair</Button>
          </Flex>
        </Flex>
      </header>

      <nav
        aria-label="Seções da organização"
        style={{ position: "sticky", top: 0, zIndex: 20, background: token.colorBgContainer, borderBottom: borda }}
      >
        <Flex
          gap={token.marginLG}
          style={{ maxWidth: LARGURA, margin: "0 auto", padding: `0 ${token.paddingLG}px`, overflowX: "auto", scrollbarWidth: "none" }}
        >
          {secoes.map((item) => {
            const ativa = item.key === secao;
            return (
              <Link
                key={item.key}
                href={hrefDaOrg(item.key, painel)}
                aria-current={ativa ? "page" : undefined}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  flexShrink: 0,
                  minHeight: 52,
                  borderBottom: `3px solid ${ativa ? token.colorPrimary : "transparent"}`,
                  color: ativa ? token.colorPrimaryText : token.colorTextSecondary,
                  fontWeight: ativa ? 600 : 500,
                  textDecoration: "none",
                }}
              >
                {item.label}
              </Link>
            );
          })}
        </Flex>
      </nav>

      <div style={{ display: "flex", alignItems: "flex-start", minWidth: 0 }}>
        <main id="conteudo-da-org" tabIndex={-1} style={{ flex: 1, minWidth: 0, outline: "none" }}>
          <Flex
            vertical
            gap={token.marginLG}
            style={{ maxWidth: LARGURA, margin: "0 auto", padding: `${token.paddingLG}px ${token.paddingLG}px ${token.paddingXL}px` }}
          >
            <Typography.Title level={1} style={{ margin: 0, fontSize: token.fontSizeHeading2 }}>
              {atual.label}
            </Typography.Title>
            {children}
            <Flex wrap gap={token.margin} style={{ borderTop: borda, paddingTop: token.padding }}>
              <Link href="/termos">Termos de uso</Link>
              <Link href={site.docsUrl}>Documentação</Link>
              <Link href={site.github}>Código aberto</Link>
            </Flex>
          </Flex>
        </main>
        {painel && screens.lg && (
          <aside
            id="painel-do-assistente"
            aria-label="Assistente de regras"
            style={{
              position: "sticky",
              top: 55,
              width: LARGURA_DO_PAINEL,
              flexShrink: 0,
              height: "calc(100dvh - 55px)",
              background: token.colorBgContainer,
              borderInlineStart: borda,
            }}
          >
            <PainelDoAssistente aoFechar={() => alternarPainel(false)} podeDecidir={org.my_areas.includes("auditoria")} />
          </aside>
        )}
      </div>
      {operadora && !screens.lg && (
        <Drawer
          open={painel}
          placement="right"
          size="100%"
          closable={false}
          onClose={() => alternarPainel(false)}
          styles={{ body: { padding: 0 } }}
        >
          <div id="painel-do-assistente">
            <PainelDoAssistente aoFechar={() => alternarPainel(false)} podeDecidir={org.my_areas.includes("auditoria")} />
          </div>
        </Drawer>
      )}
    </div>
  );
}
