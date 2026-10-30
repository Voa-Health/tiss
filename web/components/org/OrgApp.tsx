"use client";

import { Button, Card, Flex, Result, Skeleton, theme, Typography } from "antd";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect } from "react";
import { useRecurso } from "@/lib/org/cliente";
import type { CatalogoDeOrgs, EstadoDaOrg } from "@/lib/org/tipos";
import { KeysSection } from "./KeysSection";
import { MembersSection } from "./MembersSection";
import { Onboarding } from "./Onboarding";
import { OrgCasca, sair } from "./OrgCasca";
import { OrgLogin } from "./OrgLogin";
import { OverviewSection } from "./OverviewSection";
import { hrefDaOrg, ROTULO_DO_TIPO, secaoValida, type PacoteDeRegras } from "./secoes";
import { RulesSection } from "./RulesSection";
import { AuditoriaSection } from "./AuditoriaSection";
import { ContasSection } from "./ContasSection";
import { TissSection } from "./TissSection";
import { UsageSection } from "./UsageSection";
import { BillingSection } from "./BillingSection";
import { MapaSection } from "./MapaSection";

type Props = {
  configurado: boolean;
  conectado: boolean;
  orgId?: string;
  secao?: string;
  painel: boolean;
  nova: boolean;
  pacotes: PacoteDeRegras[];
};

const pronta = (org: EstadoDaOrg) => org.tiss_org && org.terms.accepted;

function Carregando() {
  const { token } = theme.useToken();
  return (
    <Flex vertical gap={token.marginLG} style={{ maxWidth: 1440, margin: "0 auto", padding: token.paddingLG }}>
      <Skeleton active />
      <Skeleton active />
    </Flex>
  );
}

function FalhaDoCatalogo({ mensagem, recarregar }: { mensagem?: string; recarregar: () => void }) {
  return (
    <Result
      status="error"
      title="Não foi possível carregar a organização."
      subTitle={mensagem}
      extra={<Button type="primary" onClick={recarregar}>Tentar de novo</Button>}
    />
  );
}

function EscolhaDeOrg({ orgs }: { orgs: EstadoDaOrg[] }) {
  const { token } = theme.useToken();
  return (
    <Flex vertical align="center" style={{ minHeight: "100vh", padding: token.paddingLG, background: token.colorBgLayout }}>
      <Flex vertical gap={token.marginLG} style={{ width: "100%", maxWidth: 720 }}>
        <Flex align="center" justify="space-between" gap={token.margin}>
          <Link href="/" aria-label="tiss, página inicial" style={{ display: "inline-flex" }}>
            <Image src="/logo.svg" alt="Voa" width={88} height={24} priority />
          </Link>
          <Flex gap={token.marginSM}>
            <Button href="/org?nova=1">Nova organização</Button>
            <Button onClick={() => void sair()}>Sair</Button>
          </Flex>
        </Flex>
        <Typography.Title level={1} style={{ margin: 0, fontSize: token.fontSizeHeading2 }}>
          Escolha a organização
        </Typography.Title>
        <Card>
          <Flex vertical gap={token.marginSM}>
            {orgs.map((org) => (
              <Flex key={org.id} wrap align="center" justify="space-between" gap={token.marginSM}>
                <Typography.Text>
                  {org.name} · {ROTULO_DO_TIPO[org.type] ?? org.type_display}
                </Typography.Text>
                <Button type="primary" href={hrefDaOrg(org.id, "visao")}>Abrir</Button>
              </Flex>
            ))}
          </Flex>
        </Card>
      </Flex>
    </Flex>
  );
}

function SemOrgNaUrl({ nova }: { nova: boolean }) {
  const router = useRouter();
  const catalogo = useRecurso<CatalogoDeOrgs>("me/tiss/organization/");
  const prontas = catalogo.dados?.organizations.filter(pronta) ?? [];
  const unica = !nova && prontas.length === 1 ? prontas[0].id : null;

  useEffect(() => {
    if (unica) router.replace(hrefDaOrg(unica, "visao"));
  }, [router, unica]);

  if (catalogo.erro?.status === 401) return <OrgLogin aviso="Entre novamente." />;
  if (catalogo.carregando || unica) return <Carregando />;
  if (catalogo.erro || !catalogo.dados) return <FalhaDoCatalogo mensagem={catalogo.erro?.message} recarregar={catalogo.recarregar} />;
  if (nova || prontas.length === 0) return <Onboarding catalogo={catalogo.dados} podeVoltar={prontas.length > 0} />;
  return <EscolhaDeOrg orgs={prontas} />;
}

function NaOrg({ orgId, secao: pedida, painel, pacotes }: { orgId: string; secao?: string; painel: boolean; pacotes: PacoteDeRegras[] }) {
  const catalogo = useRecurso<CatalogoDeOrgs>("me/tiss/organization/");
  const atual = useRecurso<EstadoDaOrg>(`org/${orgId}/tiss/`);

  if (catalogo.erro?.status === 401 || atual.erro?.status === 401) return <OrgLogin aviso="Entre novamente." />;
  if (catalogo.carregando || atual.carregando) return <Carregando />;
  if (atual.erro?.status === 403 || atual.erro?.status === 404) {
    return (
      <Result
        status="403"
        title="Você não tem acesso a esta organização."
        subTitle={atual.erro.message}
        extra={<Button type="primary" href="/org">Ver suas organizações</Button>}
      />
    );
  }
  if (catalogo.erro || !catalogo.dados) return <FalhaDoCatalogo mensagem={catalogo.erro?.message} recarregar={catalogo.recarregar} />;
  if (atual.erro || !atual.dados) return <FalhaDoCatalogo mensagem={atual.erro?.message} recarregar={atual.recarregar} />;

  const org = atual.dados;
  const outras = catalogo.dados.organizations.filter((item) => item.id !== org.id && pronta(item));
  if (!pronta(org)) return <Onboarding catalogo={catalogo.dados} podeVoltar={outras.length > 0} orgInicial={org.id} />;

  const secao = secaoValida(pedida, org);
  const financeiro = org.available_areas.find((area) => area.value === "finance")?.label ?? "Financeiro";
  const podeVerCobranca = org.is_admin || org.my_areas.includes("finance");
  const secoes: Record<typeof secao, ReactNode> = {
    visao: <OverviewSection org={org} />,
    chaves: <KeysSection orgId={org.id} podeGerenciar={org.is_admin} />,
    uso: <UsageSection orgId={org.id} podeVer={podeVerCobranca} rotuloFinanceiro={financeiro} />,
    cobranca: <BillingSection orgId={org.id} podeVer={podeVerCobranca} rotuloFinanceiro={financeiro} />,
    membros: <MembersSection orgId={org.id} podeGerenciar={org.is_admin} areasDaOrg={org.available_areas} />,
    tiss: <TissSection org={org} pacotes={pacotes} />,
    regras: <RulesSection org={org} />,
    auditoria: <AuditoriaSection org={org} />,
    contas: <ContasSection org={org} />,
    mapa: <MapaSection org={org} />,
  };

  return (
    <OrgCasca org={org} outras={outras} secao={secao} painelAberto={painel}>
      {secoes[secao]}
    </OrgCasca>
  );
}

export function OrgApp({ configurado, conectado, orgId, secao, painel, nova, pacotes }: Props) {
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
  if (!orgId) return <SemOrgNaUrl nova={nova} />;
  return <NaOrg orgId={orgId} secao={secao} painel={painel} pacotes={pacotes} />;
}
