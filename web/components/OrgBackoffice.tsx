"use client";

import { Button, Grid, Layout, Menu, Result, Segmented, theme, Typography } from "antd";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { KeysSection } from "@/components/org/KeysSection";
import { MembersSection } from "@/components/org/MembersSection";
import { OverviewSection } from "@/components/org/OverviewSection";
import { TissSection } from "@/components/org/TissSection";
import { UsageSection } from "@/components/org/UsageSection";
import {
  isOrgSection,
  orgHref,
  orgSections,
  type OrgRole,
  type OrgSection as Section,
} from "@/components/org/types";
import { loadOrg, type OrgData, type OrgDemoState } from "@/lib/org-mock";
import type { RulePack } from "@/lib/rule-packs";

export function OrgBackoffice({
  packs,
  section: requestedSection,
  role,
  demoState,
}: {
  packs: RulePack[];
  section?: string;
  role: OrgRole;
  demoState: OrgDemoState;
}) {
  const router = useRouter();
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const [data, setData] = useState<OrgData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const loadId = useRef(0);
  const section: Section = isOrgSection(requestedSection) ? requestedSection : "visao";
  const href = (nextSection: Section, nextRole: OrgRole = role) =>
    orgHref(nextSection, nextRole, demoState);

  useEffect(() => {
    const request = ++loadId.current;
    void loadOrg(demoState)
      .then((result) => {
        if (request === loadId.current) {
          setData(result);
          setLoadError(false);
        }
      })
      .catch(() => {
        if (request === loadId.current) setLoadError(true);
      })
      .finally(() => {
        if (request === loadId.current) setLoading(false);
      });
    return () => {
      loadId.current += 1;
    };
  }, [demoState]);

  function selectSection(value: string) {
    if (isOrgSection(value)) router.push(href(value));
  }

  function selectRole(value: string) {
    const nextRole: OrgRole = value === "membro" ? "membro" : "admin";
    router.push(href(section, nextRole));
  }

  function retry() {
    const request = ++loadId.current;
    setLoading(true);
    setLoadError(false);
    setData(null);
    void loadOrg("normal")
      .then((result) => {
        if (request === loadId.current) setData(result);
      })
      .catch(() => {
        if (request === loadId.current) setLoadError(true);
      })
      .finally(() => {
        if (request === loadId.current) setLoading(false);
      });
  }

  let content: ReactNode = <LoadingSkeleton />;
  if (!loading && loadError) {
    content = (
      <Result
        status="error"
        title="Não foi possível carregar a organização."
        extra={
          <Button type="primary" onClick={retry}>
            Tentar novamente
          </Button>
        }
      />
    );
  } else if (!loading && data) {
    const sections: Record<Section, ReactNode> = {
      visao: <OverviewSection org={data.org} />,
      chaves: <KeysSection initialKeys={data.keys} role={role} />,
      uso: <UsageSection days={data.usage} />,
      membros: <MembersSection initialMembers={data.members} role={role} />,
      tiss: <TissSection settings={data.tiss} packs={packs} />,
    };
    content = (
      <div style={{ minWidth: 0 }}>
        {orgSections.map(({ key }) => (
          <section key={key} hidden={key !== section}>
            {sections[key]}
          </section>
        ))}
      </div>
    );
  }

  const menuItems = orgSections.map(({ key, label }) => ({ key, label }));
  const roleOptions = [
    { label: "Administrador", value: "admin" },
    { label: "Membro", value: "membro" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: token.marginLG }}>
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          flexWrap: "wrap",
          justifyContent: "space-between",
          alignItems: "center",
          gap: token.margin,
        }}
      >
        <Typography.Text>
          Visualizando como {role === "admin" ? "administrador" : "membro"}
        </Typography.Text>
        <Segmented
          aria-label="Papel de visualização"
          options={roleOptions}
          value={role}
          onChange={selectRole}
        />
      </div>
      {!screens.md && (
        <Segmented
          block
          size="small"
          aria-label="Seções da organização"
          options={orgSections.map(({ key, mobileLabel }) => ({
            label: mobileLabel,
            value: key,
          }))}
          value={section}
          onChange={selectSection}
        />
      )}
      <Layout
        hasSider={screens.md}
        style={{
          minWidth: 0,
          overflow: "hidden",
          border: `${token.lineWidth}px ${token.lineType} ${token.colorBorderSecondary}`,
          borderRadius: token.borderRadiusLG,
          background: token.colorBgContainer,
        }}
      >
        {screens.md && (
          <Layout.Sider
            width={token.sizeXXL * 4}
            theme="light"
            style={{
              background: token.colorBgContainer,
              borderInlineEnd: `${token.lineWidth}px ${token.lineType} ${token.colorBorderSecondary}`,
            }}
          >
            <Menu
              mode="inline"
              selectedKeys={[section]}
              items={menuItems}
              onClick={({ key }) => selectSection(key)}
              style={{ borderInlineEnd: 0 }}
            />
          </Layout.Sider>
        )}
        <Layout.Content
          style={{
            minWidth: 0,
            padding: token.paddingLG,
            background: token.colorBgContainer,
          }}
        >
          {content}
        </Layout.Content>
      </Layout>
    </div>
  );
}
