"use client";

import { Button, Flex, Result, Skeleton, theme } from "antd";
import type { ReactNode } from "react";
import { useRecurso } from "@/lib/org/cliente";
import type { CatalogoDeOrgs, EstadoDaOrg } from "@/lib/org/tipos";
import { KeysSection } from "./KeysSection";
import { MembersSection } from "./MembersSection";
import { Onboarding } from "./Onboarding";
import { OrgCasca } from "./OrgCasca";
import { OrgLogin } from "./OrgLogin";
import { OverviewSection } from "./OverviewSection";
import { secaoValida, type PacoteDeRegras } from "./secoes";
import { TissSection } from "./TissSection";
import { UsageSection } from "./UsageSection";

type Props = {
  configurado: boolean;
  conectado: boolean;
  secao?: string;
  painel: boolean;
  nova: boolean;
  pacotes: PacoteDeRegras[];
};

function Carregando() {
  const { token } = theme.useToken();
  return (
    <Flex vertical gap={token.marginLG} style={{ maxWidth: 1440, margin: "0 auto", padding: token.paddingLG }}>
      <Skeleton active />
      <Skeleton active />
    </Flex>
  );
}

function OrgConectada({ secao: pedida, painel, nova, pacotes }: Omit<Props, "configurado" | "conectado">) {
  const catalogo = useRecurso<CatalogoDeOrgs>("tiss/organizations/");
  const atual = useRecurso<EstadoDaOrg>("tiss/org/");

  if (catalogo.erro?.status === 401 || atual.erro?.status === 401) return <OrgLogin aviso="Entre novamente." />;
  if (catalogo.carregando || atual.carregando) return <Carregando />;
  if (catalogo.erro || !catalogo.dados) {
    return (
      <Result
        status="error"
        title="Não foi possível carregar a organização."
        subTitle={catalogo.erro?.message}
        extra={<Button type="primary" onClick={catalogo.recarregar}>Tentar de novo</Button>}
      />
    );
  }

  const org = atual.dados;
  const pronta = Boolean(org?.tiss_org && org.terms.accepted);
  if (!org || !pronta || nova) return <Onboarding catalogo={catalogo.dados} podeVoltar={pronta} />;

  const secao = secaoValida(pedida);
  const outras = catalogo.dados.organizations.filter((item) => item.id !== org.id && item.tiss_org && item.terms.accepted);
  const financeiro = org.available_areas.find((area) => area.value === "finance")?.label ?? "Financeiro";
  const secoes: Record<typeof secao, ReactNode> = {
    visao: <OverviewSection org={org} />,
    chaves: <KeysSection podeGerenciar={org.is_admin} />,
    uso: <UsageSection podeVer={org.is_admin || org.my_areas.includes("finance")} rotuloFinanceiro={financeiro} />,
    membros: <MembersSection podeGerenciar={org.is_admin} areasDaOrg={org.available_areas} />,
    tiss: <TissSection org={org} pacotes={pacotes} />,
  };

  return (
    <OrgCasca org={org} outras={outras} secao={secao} painelAberto={painel}>
      {secoes[secao]}
    </OrgCasca>
  );
}

export function OrgApp({ configurado, conectado, ...resto }: Props) {
  if (!configurado) {
    return (
      <Result
        status="warning"
        title="Painel da organização indisponível"
        subTitle="Este ambiente não tem o backend da conta Voa configurado."
        extra={<Button href="/">Página inicial</Button>}
      />
    );
  }
  if (!conectado) return <OrgLogin />;
  return <OrgConectada {...resto} />;
}
