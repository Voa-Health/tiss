"use client";

import { Alert, Button, Checkbox, Flex, Form, Input, Select, Typography } from "antd";
import { useState } from "react";
import { apiBase } from "@/lib/site";
import { documentTypes, moduleContent, monthlyVolumes, type ModuleSlug } from "@/lib/modules";

type WaitlistValues = {
  email: string;
  empresa: string;
  volume_mensal: string;
  tipos_documento?: string[];
};

export function WaitlistForm({ module }: { module: ModuleSlug }) {
  const [form] = Form.useForm<WaitlistValues>();
  const [received, setReceived] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(values: WaitlistValues) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${apiBase}/v1/lista-de-espera`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ modulo: module, ...values }),
      });
      const body = await response.json().catch(() => ({}));
      if (response.status === 202) {
        setReceived(true);
      } else if (response.status === 429) {
        setError("Muitas tentativas. Tente mais tarde.");
      } else {
        setError(body.erro?.mensagem ?? "Não foi possível enviar a inscrição.");
      }
    } catch {
      setError("Não foi possível conectar. Tente mais tarde.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Flex vertical gap={16}>
      <Typography.Title level={2}>Avise-me no lançamento</Typography.Title>
      {received ? (
        <Alert
          type="success"
          showIcon
          title="Inscrição recebida. Avisaremos por e-mail no lançamento."
        />
      ) : (
        <Form
          form={form}
          layout="vertical"
          onFinish={(values) => void submit(values)}
          style={{ maxWidth: 560 }}
        >
          <Form.Item
            label="E-mail"
            name="email"
            rules={[
              { required: true, message: "Informe seu e-mail." },
              { type: "email", message: "Informe um e-mail válido." },
            ]}
          >
            <Input type="email" autoComplete="email" />
          </Form.Item>
          <Form.Item
            label="Empresa"
            name="empresa"
            rules={[{ required: true, whitespace: true, message: "Informe sua empresa." }]}
          >
            <Input autoComplete="organization" />
          </Form.Item>
          <Form.Item
            label={moduleContent[module].volumeLabel}
            name="volume_mensal"
            rules={[{ required: true, message: "Selecione o volume mensal." }]}
          >
            <Select options={monthlyVolumes.map(({ value, label }) => ({ value, label }))} />
          </Form.Item>
          {module === "extrator" && (
            <Form.Item
              label="Tipos de documento"
              name="tipos_documento"
              rules={[{ required: true, message: "Selecione ao menos um tipo de documento." }]}
            >
              <Checkbox.Group options={documentTypes.map(({ value, label }) => ({ value, label }))} />
            </Form.Item>
          )}
          {error && <Alert type="error" showIcon title={error} style={{ marginBlockEnd: 16 }} />}
          <Button type="primary" htmlType="submit" loading={loading}>
            Entrar na lista de espera
          </Button>
          <Typography.Paragraph type="secondary" style={{ marginBlockStart: 12 }}>
            E-mail e empresa usados só para falar sobre o módulo. Consulte os{" "}
            <a href="/termos">termos</a>.
          </Typography.Paragraph>
        </Form>
      )}
    </Flex>
  );
}
