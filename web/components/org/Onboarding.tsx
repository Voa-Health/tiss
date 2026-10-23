"use client";

import {
  AppstoreOutlined,
  CodeOutlined,
  ExperimentOutlined,
  GlobalOutlined,
  MedicineBoxOutlined,
  SafetyCertificateOutlined,
  ShopOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Alert, Button, Card, Checkbox, Col, Flex, Form, Input, Row, Select, theme, Typography } from "antd";
import Image from "next/image";
import Link from "next/link";
import { type ReactNode, useState } from "react";
import { abrirDeNovo, FalhaDoPedido, pedir } from "@/lib/org/cliente";
import type { CatalogoDeOrgs, EstadoDaOrg, Subtipo } from "@/lib/org/tipos";
import { sair } from "./OrgCasca";
import { ROTULO_DO_TIPO } from "./secoes";

type Campos = {
  destino: string;
  name?: string;
  subtype: string;
  cnpj: string;
  registro_ans?: string;
  aceite: boolean;
};

const NOVA = "nova";

const ICONE_DO_SUBTIPO: Record<string, ReactNode> = {
  hospital: <MedicineBoxOutlined />,
  clinica: <ShopOutlined />,
  laboratorio: <ExperimentOutlined />,
  profissional: <UserOutlined />,
  operadora: <SafetyCertificateOutlined />,
  autogestao: <TeamOutlined />,
  healthtech_consultoria: <CodeOutlined />,
  sus_governo: <GlobalOutlined />,
  outro: <AppstoreOutlined />,
};

const GRUPOS = [
  { rotulo: "Prestador", tipos: ["prov"] },
  { rotulo: "Operadora", tipos: ["pay"] },
  { rotulo: "Outros", tipos: ["bus", "govt", "other"] },
];

function PapelDaOrg({
  subtipos,
  value,
  onChange,
}: {
  subtipos: Subtipo[];
  value?: string;
  onChange?: (valor: string) => void;
}) {
  const { token } = theme.useToken();
  const conhecidos = new Set(GRUPOS.flatMap((grupo) => grupo.tipos));
  const grupos = [
    ...GRUPOS.map((grupo) => ({ ...grupo, itens: subtipos.filter((item) => grupo.tipos.includes(item.type)) })),
    { rotulo: "Outros tipos", tipos: [], itens: subtipos.filter((item) => !conhecidos.has(item.type)) },
  ].filter((grupo) => grupo.itens.length > 0);

  return (
    <Flex vertical gap={token.margin} role="radiogroup" aria-label="Tipo da sua empresa">
      {grupos.map((grupo) => (
        <Flex key={grupo.rotulo} vertical gap={token.marginXS}>
          <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
            {grupo.rotulo}
          </Typography.Text>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: token.marginXS }}>
            {grupo.itens.map((item) => {
              const marcado = value === item.code;
              return (
                <button
                  key={item.code}
                  type="button"
                  role="radio"
                  aria-checked={marcado}
                  onClick={() => onChange?.(item.code)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: token.marginXS,
                    minWidth: 0,
                    minHeight: 48,
                    padding: `${token.paddingXS}px ${token.paddingSM}px`,
                    border: `1px solid ${marcado ? token.colorPrimary : token.colorBorder}`,
                    borderRadius: token.borderRadiusLG,
                    background: marcado ? token.colorPrimaryBg : token.colorBgContainer,
                    boxShadow: marcado ? `0 0 0 1px ${token.colorPrimary}` : "none",
                    color: marcado ? token.colorPrimaryText : token.colorText,
                    cursor: "pointer",
                    font: "inherit",
                    textAlign: "left",
                    transition: `border-color ${token.motionDurationMid}, background ${token.motionDurationMid}`,
                  }}
                >
                  <span style={{ fontSize: token.fontSizeLG, color: marcado ? token.colorPrimary : token.colorTextSecondary }}>
                    {ICONE_DO_SUBTIPO[item.code] ?? <AppstoreOutlined />}
                  </span>
                  <span style={{ minWidth: 0, lineHeight: token.lineHeightSM }}>{item.display.replaceAll("/", "/\u200b")}</span>
                </button>
              );
            })}
          </div>
        </Flex>
      ))}
    </Flex>
  );
}

export function Onboarding({ catalogo, podeVoltar }: { catalogo: CatalogoDeOrgs; podeVoltar: boolean }) {
  const { token } = theme.useToken();
  const [form] = Form.useForm<Campos>();
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const prontas = catalogo.organizations.filter((org) => org.tiss_org && org.terms.accepted);
  const aceitaveis = catalogo.organizations.filter((org) => org.is_admin && !(org.tiss_org && org.terms.accepted));
  const destino = Form.useWatch("destino", form) ?? NOVA;
  const subtipo = Form.useWatch("subtype", form);
  const tipo = catalogo.subtypes.find((item) => item.code === subtipo)?.type;

  function preencher(id: string) {
    const org = aceitaveis.find((item) => item.id === id);
    if (!org) return;
    form.setFieldsValue({
      cnpj: org.cnpj || undefined,
      registro_ans: org.registro_ans || undefined,
      subtype: org.subtype || undefined,
    });
  }

  async function abrir(org: EstadoDaOrg) {
    try {
      await pedir("/api/org/trocar", { method: "POST", body: { organization_id: org.id } });
      abrirDeNovo();
    } catch (motivo) {
      setErro(motivo instanceof FalhaDoPedido ? motivo.message : "Não foi possível abrir a organização.");
    }
  }

  async function enviar(valores: Campos) {
    const nova = (valores.destino ?? NOVA) === NOVA;
    setEnviando(true);
    setErro("");
    try {
      await pedir("tiss/organizations/", {
        method: "POST",
        body: {
          ...(nova ? { name: valores.name } : { organization_id: valores.destino }),
          subtype: valores.subtype,
          cnpj: valores.cnpj,
          ...(tipo === "pay" ? { registro_ans: valores.registro_ans } : {}),
          accept_terms_version: catalogo.terms_version,
        },
      });
      abrirDeNovo();
    } catch (motivo) {
      if (motivo instanceof FalhaDoPedido) {
        const nomes = new Set(["name", "subtype", "cnpj", "registro_ans"]);
        const campos = Object.entries(motivo.campos).filter(([campo]) => nomes.has(campo));
        form.setFields(campos.map(([name, mensagem]) => ({ name: name as keyof Campos, errors: [mensagem] })));
        if (campos.length === 0) setErro(motivo.message);
      } else {
        setErro("Não foi possível criar a organização.");
      }
      setEnviando(false);
    }
  }

  return (
    <Flex vertical align="center" style={{ minHeight: "100vh", padding: token.paddingLG, background: token.colorBgLayout }}>
      <Flex vertical gap={token.marginLG} style={{ width: "100%", maxWidth: 720 }}>
        <Flex align="center" justify="space-between" gap={token.margin}>
          <Link href="/" aria-label="voa-tiss, página inicial" style={{ display: "inline-flex" }}>
            <Image src="/logo.svg" alt="Voa" width={88} height={24} priority />
          </Link>
          <Flex gap={token.marginSM}>
            {podeVoltar && <Button href="/org">Voltar ao painel</Button>}
            <Button onClick={() => void sair()}>Sair</Button>
          </Flex>
        </Flex>
        <Flex vertical gap={token.marginXXS}>
          <Typography.Title level={1} style={{ margin: 0, fontSize: token.fontSizeHeading2 }}>
            Sua organização no voa-tiss
          </Typography.Title>
          <Typography.Text type="secondary">
            Diga quem a organização é para receber o produto certo: prestadores validam e recorrem,
            operadoras analisam contas e autorizações.
          </Typography.Text>
        </Flex>
        {prontas.length > 0 && (
          <Card title="Abrir uma organização">
            <Flex vertical gap={token.marginSM}>
              {prontas.map((org) => (
                <Flex key={org.id} wrap align="center" justify="space-between" gap={token.marginSM}>
                  <Typography.Text>
                    {org.name} · {ROTULO_DO_TIPO[org.type] ?? org.type_display}
                  </Typography.Text>
                  <Button onClick={() => void abrir(org)}>Abrir</Button>
                </Flex>
              ))}
            </Flex>
          </Card>
        )}
        <Card title="Criar organização">
          {erro && <Alert type="error" showIcon title={erro} style={{ marginBottom: token.margin }} />}
          <Form<Campos>
            form={form}
            layout="vertical"
            initialValues={{ destino: NOVA, aceite: false }}
            onFinish={(valores) => void enviar(valores)}
          >
            {aceitaveis.length > 0 && (
              <Form.Item name="destino" label="Organização">
                <Select
                  onChange={preencher}
                  options={[
                    { value: NOVA, label: "Nova organização" },
                    ...aceitaveis.map((org) => ({ value: org.id, label: `${org.name} (já existe na Voa)` })),
                  ]}
                />
              </Form.Item>
            )}
            <Form.Item name="subtype" label="Tipo da sua empresa" rules={[{ required: true, message: "Escolha o tipo." }]}>
              <PapelDaOrg subtipos={catalogo.subtypes} />
            </Form.Item>
            {destino === NOVA && (
              <Form.Item name="name" label="Nome" rules={[{ required: true, whitespace: true, message: "Informe o nome." }]}>
                <Input autoComplete="organization" placeholder="Como a organização é conhecida" />
              </Form.Item>
            )}
            <Row gutter={token.margin}>
              <Col xs={24} sm={tipo === "pay" ? 14 : 24}>
                <Form.Item name="cnpj" label="CNPJ" rules={[{ required: true, whitespace: true, message: "Informe o CNPJ." }]}>
                  <Input inputMode="numeric" placeholder="00.000.000/0000-00" />
                </Form.Item>
              </Col>
              {tipo === "pay" && (
                <Col xs={24} sm={10}>
                  <Form.Item
                    name="registro_ans"
                    label="Registro ANS"
                    rules={[{ required: true, whitespace: true, message: "Informe o registro ANS." }]}
                  >
                    <Input inputMode="numeric" placeholder="000000" />
                  </Form.Item>
                </Col>
              )}
            </Row>
            <Form.Item
              name="aceite"
              valuePropName="checked"
              rules={[
                {
                  validator: (_, valor) => (valor ? Promise.resolve() : Promise.reject(new Error("Aceite os termos para continuar."))),
                },
              ]}
            >
              <Checkbox>
                Li e aceito os <a href={catalogo.terms_url || "/termos"} target="_blank" rel="noreferrer">termos de uso</a>{" "}
                (versão {catalogo.terms_version})
              </Checkbox>
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={enviando}>Criar organização</Button>
          </Form>
        </Card>
      </Flex>
    </Flex>
  );
}
