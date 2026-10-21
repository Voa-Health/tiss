"use client";

import { useState } from "react";
import { Alert, Button, Card, Flex, Form, Input, Tag, Typography } from "antd";

const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";

type Vinculo = {
  registro_ans: string;
  nome: string | null;
  cnes: string | null;
  nome_estabelecimento: string;
  tipo_contrato: string[];
  disponibilidade: string[];
  urgencia_emergencia: boolean;
  planos: number;
};
type Rede = { atualizado_em: string; fonte: string; total: number; operadoras: Vinculo[] };

function queryFor(value: string): string | null {
  const digits = value.replace(/\D/g, "");
  if (digits.length === 7) return `cnes=${digits}`;
  if (digits.length === 14) return `cnpj=${digits}`;
  return null;
}

async function fetchRede(query: string): Promise<Rede> {
  const response = await fetch(`${apiBase}/v1/rede?${query}`);
  const body = await response.json().catch(() => ({}));
  if (response.ok) return body as Rede;
  if (response.status === 422) throw new Error(body.erro?.mensagem ?? "CNPJ ou CNES inválido.");
  if (response.status === 429) throw new Error("Limite de chamadas atingido.");
  throw new Error("O serviço está indisponível. Tente novamente.");
}

export function NetworkSearch() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Rede | null>(null);

  async function search({ identificador }: { identificador: string }) {
    const query = queryFor(identificador ?? "");
    setResult(null);
    if (!query) {
      setError("Informe um CNPJ (14 dígitos) ou um CNES (7 dígitos).");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      setResult(await fetchRede(query));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Não foi possível conectar.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card title="Operadoras que atendem um hospital" style={{ marginBlockEnd: 24 }}>
      <Form layout="vertical" onFinish={search} requiredMark={false}>
        <Form.Item
          label="CNPJ ou CNES do estabelecimento"
          name="identificador"
          rules={[{ required: true, message: "Informe o CNPJ ou o CNES." }]}
        >
          <Input inputMode="numeric" placeholder="14 dígitos do CNPJ ou 7 do CNES" allowClear />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={loading}>
          Buscar
        </Button>
      </Form>
      {error && <Alert type="error" showIcon title={error} style={{ marginBlockStart: 16 }} />}
      {result && (
        <Flex vertical gap={8} style={{ marginBlockStart: 16 }}>
          <Typography.Text strong>
            {result.operadoras[0]?.nome_estabelecimento ?? "Estabelecimento"} · {result.total} operadora(s)
          </Typography.Text>
          {result.operadoras.length === 0 && (
            <Typography.Text>Nenhuma operadora com vínculo para este estabelecimento.</Typography.Text>
          )}
          {result.operadoras.map((item) => (
            <div key={`${item.registro_ans}-${item.cnes}`}>
              {item.registro_ans} · {item.nome ?? "Operadora sem cadastro ativo"} · {item.planos} plano(s){" "}
              {item.tipo_contrato.map((value) => (
                <Tag key={value}>{value}</Tag>
              ))}
              {item.urgencia_emergencia && <Tag color="blue">Urgência e emergência</Tag>}
            </div>
          ))}
          {result.total > result.operadoras.length && (
            <Typography.Text type="secondary">
              Exibindo {result.operadoras.length} de {result.total}.
            </Typography.Text>
          )}
          <Typography.Text type="secondary">
            Fonte: {result.fonte} · atualizado em {result.atualizado_em}
          </Typography.Text>
        </Flex>
      )}
    </Card>
  );
}
