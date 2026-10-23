"use client";

import { Alert, Button, Card, Checkbox, Flex, Form, Input, Radio, Select, theme, Typography } from "antd";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { abrirDeNovo, FalhaDoPedido, pedir } from "@/lib/org/cliente";
import type { CatalogoDeOrgs, EstadoDaOrg } from "@/lib/org/tipos";
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
            {destino === NOVA && (
              <Form.Item name="name" label="Nome" rules={[{ required: true, whitespace: true, message: "Informe o nome." }]}>
                <Input autoComplete="organization" />
              </Form.Item>
            )}
            <Form.Item name="subtype" label="Quem é a organização" rules={[{ required: true, message: "Escolha o tipo." }]}>
              <Radio.Group style={{ width: "100%" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: token.marginSM }}>
                  {catalogo.subtypes.map((item) => (
                    <Radio key={item.code} value={item.code}>
                      <Flex vertical>
                        <Typography.Text>{item.display}</Typography.Text>
                        <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                          {ROTULO_DO_TIPO[item.type] ?? item.type}
                        </Typography.Text>
                      </Flex>
                    </Radio>
                  ))}
                </div>
              </Radio.Group>
            </Form.Item>
            <Form.Item name="cnpj" label="CNPJ" rules={[{ required: true, whitespace: true, message: "Informe o CNPJ." }]}>
              <Input inputMode="numeric" placeholder="00.000.000/0000-00" />
            </Form.Item>
            {tipo === "pay" && (
              <Form.Item
                name="registro_ans"
                label="Registro ANS"
                extra="Obrigatório para operadoras e autogestões."
                rules={[{ required: true, whitespace: true, message: "Informe o registro ANS." }]}
              >
                <Input inputMode="numeric" placeholder="000000" />
              </Form.Item>
            )}
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
