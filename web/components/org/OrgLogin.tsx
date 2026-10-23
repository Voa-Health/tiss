"use client";

import { Alert, Button, Card, Checkbox, Flex, Form, Input, Segmented, theme, Typography } from "antd";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { abrirDeNovo, FalhaDoPedido, pedir } from "@/lib/org/cliente";
import { ReenviarEmail } from "./ReenviarEmail";

type Entrada = { email: string; senha: string };
type Cadastro = { nome: string; email: string; senha: string; aceite: boolean };
type Modo = "entrar" | "criar";

function FormularioDeCadastro({ aoCriar }: { aoCriar: (email: string) => void }) {
  const [form] = Form.useForm<Cadastro>();
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function criar(valores: Cadastro) {
    setEnviando(true);
    setErro("");
    try {
      const { email } = await pedir<{ email: string }>("/api/org/cadastrar", { method: "POST", body: valores });
      aoCriar(email);
    } catch (motivo) {
      if (motivo instanceof FalhaDoPedido && (motivo.campos.email || motivo.campos.senha)) {
        form.setFields(
          (["email", "senha"] as const)
            .filter((campo) => motivo.campos[campo])
            .map((campo) => ({ name: campo, errors: [motivo.campos[campo]] })),
        );
      } else {
        setErro(motivo instanceof FalhaDoPedido ? motivo.message : "Não foi possível criar a conta.");
      }
      setEnviando(false);
    }
  }

  return (
    <Form<Cadastro> form={form} layout="vertical" requiredMark={false} initialValues={{ aceite: false }} onFinish={(valores) => void criar(valores)}>
      {erro && <Alert type="error" showIcon title={erro} style={{ marginBottom: "var(--ant-margin)" }} />}
      <Form.Item name="nome" label="Seu nome" rules={[{ required: true, whitespace: true, message: "Informe seu nome." }]}>
        <Input autoComplete="name" />
      </Form.Item>
      <Form.Item name="email" label="E-mail de trabalho" rules={[{ required: true, type: "email", message: "Informe um e-mail válido." }]}>
        <Input type="email" autoComplete="email" />
      </Form.Item>
      <Form.Item
        name="senha"
        label="Senha"
        extra="Pelo menos 8 caracteres, sem ser só números."
        rules={[{ required: true, min: 8, message: "A senha precisa de pelo menos 8 caracteres." }]}
      >
        <Input.Password autoComplete="new-password" />
      </Form.Item>
      <Form.Item
        name="aceite"
        valuePropName="checked"
        rules={[{ validator: (_, valor) => (valor ? Promise.resolve() : Promise.reject(new Error("Aceite os termos para continuar."))) }]}
      >
        <Checkbox>
          Li e aceito os <a href="/termos" target="_blank" rel="noreferrer">termos de uso</a>
        </Checkbox>
      </Form.Item>
      <Button type="primary" htmlType="submit" block loading={enviando}>Criar conta</Button>
    </Form>
  );
}

export function OrgLogin({ aviso }: { aviso?: string }) {
  const { token } = theme.useToken();
  const [modo, setModo] = useState<Modo>("entrar");
  const [criada, setCriada] = useState("");
  const [erro, setErro] = useState(aviso ?? "");
  const [enviando, setEnviando] = useState(false);

  async function entrar({ email, senha }: Entrada) {
    setEnviando(true);
    setErro("");
    try {
      await pedir("/api/org/entrar", { method: "POST", body: { email, senha } });
      abrirDeNovo();
    } catch (motivo) {
      setErro(motivo instanceof FalhaDoPedido ? motivo.message : "Não foi possível entrar.");
      setEnviando(false);
    }
  }

  let conteudo;
  if (criada) {
    conteudo = (
      <Flex vertical gap={token.margin}>
        <Alert
          type="success"
          showIcon
          title="Confira seu e-mail"
          description={`Mandamos um link para ${criada}. Ao abrir, a conta é confirmada e você segue direto para cadastrar a organização.`}
        />
        <ReenviarEmail email={criada} />
        <Button type="link" onClick={() => { setCriada(""); setModo("entrar"); }}>Já confirmei, quero entrar</Button>
      </Flex>
    );
  } else if (modo === "criar") {
    conteudo = <FormularioDeCadastro aoCriar={setCriada} />;
  } else {
    conteudo = (
      <>
        {erro && <Alert type="error" showIcon title={erro} />}
        <Form<Entrada> layout="vertical" requiredMark={false} onFinish={(valores) => void entrar(valores)}>
          <Form.Item
            name="email"
            label="E-mail"
            rules={[{ required: true, type: "email", message: "Informe um e-mail válido." }]}
          >
            <Input type="email" autoComplete="username" />
          </Form.Item>
          <Form.Item name="senha" label="Senha" rules={[{ required: true, message: "Informe a senha." }]}>
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={enviando}>Entrar</Button>
        </Form>
      </>
    );
  }

  return (
    <Flex
      vertical
      align="center"
      justify="center"
      style={{ minHeight: "100vh", padding: token.paddingLG, background: token.colorBgLayout }}
    >
      <Card style={{ width: "100%", maxWidth: 440 }}>
        <Flex vertical gap={token.margin}>
          <Link href="/" aria-label="tiss, página inicial" style={{ display: "inline-flex" }}>
            <Image src="/logo.svg" alt="Voa" width={88} height={24} priority />
          </Link>
          <Flex vertical gap={token.marginXXS}>
            <Typography.Title level={1} style={{ margin: 0, fontSize: token.fontSizeHeading3 }}>
              Organização tiss
            </Typography.Title>
            <Typography.Text type="secondary">
              {modo === "criar"
                ? "Crie uma conta Voa para cadastrar sua organização. Não precisa de plano."
                : "Entre com a conta Voa para gerenciar chaves, uso e membros da sua organização."}
            </Typography.Text>
          </Flex>
          {!criada && (
            <Segmented<Modo>
              block
              value={modo}
              onChange={setModo}
              options={[{ label: "Entrar", value: "entrar" }, { label: "Criar conta", value: "criar" }]}
            />
          )}
          {conteudo}
          <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
            A senha vai direto para a Voa; este site não a guarda.
          </Typography.Text>
        </Flex>
      </Card>
    </Flex>
  );
}
