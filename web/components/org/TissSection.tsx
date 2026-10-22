"use client";

import { Alert, App, Button, Card, Flex, Form, Input, InputNumber, Result, Skeleton, theme, Typography } from "antd";
import Link from "next/link";
import { useEffect, useState } from "react";
import { FalhaDoPedido, pedir, useRecurso } from "@/lib/org/cliente";
import type { ConfiguracoesTiss, EstadoDaOrg } from "@/lib/org/tipos";
import { hrefDaOrg, type PacoteDeRegras } from "./secoes";

type Campos = { registro_ans?: string; padrao?: string; max_guias_por_lote?: number | null };

function RegrasDaOperadora({ registro, pacotes }: { registro: string; pacotes: PacoteDeRegras[] }) {
  const pacote = pacotes.find((item) => item.registro === registro.replace(/\D/g, ""));
  return (
    <Card title="Regras de envio">
      <Flex vertical align="flex-start" gap="var(--ant-margin)">
        <Typography.Text>
          {pacote
            ? `O pacote aberto do registro ${pacote.registro} tem ${pacote.regras} regras.`
            : "Nenhum pacote aberto de regras para este registro ANS."}
        </Typography.Text>
        <Flex wrap gap="var(--ant-margin-sm)">
          {pacote && <Button href={`/operadoras/${pacote.registro}`}>Ver pacote</Button>}
          <Link href={hrefDaOrg("tiss", true)}>
            <Button type="primary">Cadastrar com o assistente</Button>
          </Link>
        </Flex>
      </Flex>
    </Card>
  );
}

export function TissSection({ org, pacotes }: { org: EstadoDaOrg; pacotes: PacoteDeRegras[] }) {
  const { token } = theme.useToken();
  const { message } = App.useApp();
  const [form] = Form.useForm<Campos>();
  const configuracoes = useRecurso<ConfiguracoesTiss>("tiss/org/settings/");
  const [salvando, setSalvando] = useState(false);
  const operadora = org.type === "pay";
  const podeEditar = org.is_admin;

  useEffect(() => {
    if (configuracoes.dados) form.setFieldsValue(configuracoes.dados);
  }, [configuracoes.dados, form]);

  async function salvar(valores: Campos) {
    const atual = configuracoes.dados;
    const mudou = Object.fromEntries(
      Object.entries(valores).filter(([campo, valor]) => atual?.[campo as keyof ConfiguracoesTiss] !== (valor ?? null)),
    );
    if (!Object.keys(mudou).length) return;
    setSalvando(true);
    try {
      await pedir("tiss/org/settings/", { method: "PATCH", body: mudou });
      message.success("Configurações salvas.");
      configuracoes.recarregar();
    } catch (erro) {
      if (erro instanceof FalhaDoPedido && Object.keys(erro.campos).length) {
        form.setFields(Object.entries(erro.campos).map(([name, mensagem]) => ({ name: name as keyof Campos, errors: [mensagem] })));
      } else {
        message.error(erro instanceof FalhaDoPedido ? erro.message : "Não foi possível salvar.");
      }
    } finally {
      setSalvando(false);
    }
  }

  let conteudo;
  if (configuracoes.erro) {
    conteudo = <Result status="error" title="Não foi possível carregar as configurações." subTitle={configuracoes.erro.message}
      extra={<Button onClick={configuracoes.recarregar}>Tentar de novo</Button>} />;
  } else if (!configuracoes.dados) {
    conteudo = <Skeleton active />;
  } else {
    conteudo = (
      <Form<Campos> form={form} layout="vertical" disabled={!podeEditar} onFinish={(valores) => void salvar(valores)} style={{ maxWidth: 480 }}>
        {operadora && (
          <Form.Item name="registro_ans" label="Registro ANS" rules={[{ required: true, whitespace: true, message: "Informe o registro ANS." }]}>
            <Input inputMode="numeric" />
          </Form.Item>
        )}
        <Form.Item name="padrao" label="Padrão TISS" extra="Versão usada quando o lote não declara a sua.">
          <Input placeholder="4.03.00" />
        </Form.Item>
        <Form.Item name="max_guias_por_lote" label="Máximo de guias por lote">
          <InputNumber min={1} style={{ width: "100%" }} />
        </Form.Item>
        {podeEditar && <Button type="primary" htmlType="submit" loading={salvando}>Salvar</Button>}
      </Form>
    );
  }

  return (
    <Flex vertical gap={token.marginLG}>
      <Card title="Validação" styles={{ body: { display: "flex", flexDirection: "column", gap: token.margin } }}>
        {!podeEditar && <Alert type="info" showIcon title="Só quem tem a Área Administração altera as configurações." />}
        {conteudo}
      </Card>
      {operadora && <RegrasDaOperadora registro={org.registro_ans} pacotes={pacotes} />}
    </Flex>
  );
}
