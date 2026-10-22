"use client";

import {
  Alert,
  Button,
  Card,
  Descriptions,
  Flex,
  Form,
  Grid,
  Input,
  InputNumber,
  Select,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  theme,
  Typography,
} from "antd";
import { useState } from "react";
import { apiBase, site } from "@/lib/site";
import { track } from "@/lib/analytics";

const scenarios = [
  { value: "aprovado", label: "Aprovado" },
  { value: "duplicidade", label: "Duplicidade" },
  { value: "carteirinha_vencida", label: "Carteirinha vencida" },
  { value: "sem_autorizacao", label: "Sem autorização" },
  { value: "falha_transitoria", label: "Falha transitória" },
  { value: "falha_permanente", label: "Falha permanente" },
];

type Finding = {
  severity: "error" | "warning";
  code: string;
  message: string;
  xpath?: string | null;
  pointer?: string | null;
  guia?: string | null;
};
type ValidationReport = { valid: boolean; findings: Finding[] };
type SandboxResult = {
  aceito: boolean;
  protocolo: string | null;
  numero_protocolo: string | null;
  numero_lote: string | null;
  cenario: string;
  findings: Finding[];
};
type Failure = { status: number; body: { erro?: { mensagem?: string } } };

class RequestFailure extends Error {
  constructor(
    readonly status: number,
    readonly body: Failure["body"],
  ) {
    super(body.erro?.mensagem ?? "Falha na solicitação.");
  }
}

async function requestJson(url: string, init: RequestInit): Promise<Record<string, unknown>> {
  const response = await fetch(url, init);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new RequestFailure(response.status, body);
  return body;
}

function failureText(error: unknown): { message: string; limited: boolean } {
  if (error instanceof RequestFailure) {
    if (error.status === 401) return { message: "A chave informada é inválida.", limited: false };
    if (error.status === 422) {
      return { message: error.body.erro?.mensagem ?? "A entrada não é válida.", limited: false };
    }
    if (error.status === 429) return { message: "Limite de chamadas atingido.", limited: true };
    if (error.status >= 500) return { message: "O serviço está indisponível. Tente novamente.", limited: false };
  }
  return { message: "Não foi possível conectar. Verifique a conexão e tente novamente.", limited: false };
}

function ErrorNotice({ error }: { error: unknown }) {
  const { message, limited } = failureText(error);
  return (
    <Alert
      type="error"
      showIcon
      title={message}
      description={limited ? <a href="/entrar">Entre com Voa para consultar o acesso.</a> : undefined}
    />
  );
}

function FindingsTable({ findings }: { findings: Finding[] }) {
  return (
    <Table
      rowKey={(row, index) => `${index}-${row.code}`}
      dataSource={findings}
      pagination={{ pageSize: 8 }}
      locale={{ emptyText: "Nenhum achado." }}
      columns={[
        {
          title: "Severidade",
          dataIndex: "severity",
          render: (severity: Finding["severity"]) => (
            <Tag color={severity === "error" ? "red" : "gold"}>{severity === "error" ? "Erro" : "Aviso"}</Tag>
          ),
        },
        { title: "Código", dataIndex: "code" },
        { title: "Mensagem", dataIndex: "message" },
        {
          title: "Localização",
          render: (_value: unknown, row: Finding) => row.xpath ?? row.pointer ?? row.guia ?? "—",
        },
      ]}
    />
  );
}

function ExampleButtons({
  onLoad,
}: {
  onLoad: (value: string) => void;
}) {
  return (
    <Form.Item label="Exemplos XML">
      <Space wrap>
        <Button onClick={() => onLoad("error")}>Lote com achados</Button>
        <Button onClick={() => onLoad("valid")}>Lote válido</Button>
      </Space>
    </Form.Item>
  );
}

function XmlTextArea({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const { token } = theme.useToken();
  return (
    <Input.TextArea
      aria-label="XML do lote"
      rows={12}
      wrap="off"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      style={{ fontFamily: token.fontFamilyCode, whiteSpace: "pre", overflowX: "auto" }}
    />
  );
}

function ValidationTab({
  apiKey,
  errorExample,
  validExample,
}: {
  apiKey: string;
  errorExample: string;
  validExample: string;
}) {
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const [xml, setXml] = useState(errorExample);
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  async function validate() {
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (apiKey) headers.Authorization = `Bearer ${apiKey}`;
      const result = await requestJson(`${apiBase}/v1/validate`, {
        method: "POST",
        headers,
        body: JSON.stringify({ xml }),
      });
      const validation = result as ValidationReport;
      track("tiss_playground_validate", {
        resultado: validation.findings.length ? "com_achados" : "valido",
      });
      setReport(validation);
    } catch (failure) {
      track("tiss_playground_validate", { resultado: "erro" });
      setError(failure);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card style={{ minWidth: 0, maxWidth: "100%" }}>
      <Form layout="vertical" style={{ minWidth: 0 }}>
        {!apiKey && (
          <Alert
            type="info"
            showIcon
            title="Sem chave, apenas a operadora simulada funciona."
            description={<a href="/entrar">Entre com Voa para validar lotes.</a>}
            style={{ marginBlockEnd: token.margin }}
          />
        )}
        <Form.Item label="XML do lote">
          <XmlTextArea value={xml} onChange={setXml} />
        </Form.Item>
        <ExampleButtons onLoad={(which) => setXml(which === "error" ? errorExample : validExample)} />
        <Flex
          vertical={!screens.md}
          align={screens.md ? "center" : "flex-start"}
          gap={token.margin}
        >
          <Button type="primary" disabled={!apiKey || !xml.trim()} loading={loading} onClick={validate}>
            Validar lote
          </Button>
          {!loading && !error && !report && (
            <Typography.Text type="secondary">Envie o XML para consultar os achados.</Typography.Text>
          )}
        </Flex>
        {loading && <Spin aria-label="Validando lote" style={{ display: "block", marginBlock: token.margin }} />}
        {error !== null && <div style={{ marginBlockStart: token.margin }}><ErrorNotice error={error} /></div>}
        {report && (
          <div style={{ marginBlockStart: token.margin }}>
            {report.findings.length ? (
              <FindingsTable findings={report.findings} />
            ) : (
              <Alert type="success" showIcon title="Lote válido, sem achados." />
            )}
          </div>
        )}
      </Form>
    </Card>
  );
}

function SandboxTab({ apiKey, validExample }: { apiKey: string; validExample: string }) {
  const { token } = theme.useToken();
  const [xml, setXml] = useState(validExample);
  const [scenario, setScenario] = useState("aprovado");
  const [attempt, setAttempt] = useState(1);
  const [result, setResult] = useState<SandboxResult | null>(null);
  const [statement, setStatement] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [statementLoading, setStatementLoading] = useState(false);

  async function submit() {
    setLoading(true);
    setError(null);
    setResult(null);
    setStatement("");
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (apiKey) headers.Authorization = `Bearer ${apiKey}`;
      const value = await requestJson(`${apiBase}/v1/sandbox/lotes`, {
        method: "POST",
        headers,
        body: JSON.stringify({ xml, cenario: scenario, tentativa: attempt }),
      });
      setResult(value as SandboxResult);
    } catch (failure) {
      setError(failure);
    } finally {
      setLoading(false);
    }
  }

  async function fetchStatement() {
    if (!result?.protocolo) return;
    setStatementLoading(true);
    setError(null);
    try {
      const headers: Record<string, string> = {};
      if (apiKey) headers.Authorization = `Bearer ${apiKey}`;
      const value = await requestJson(
        `${apiBase}/v1/sandbox/lotes/${encodeURIComponent(result.protocolo)}/demonstrativo`,
        { headers },
      );
      setStatement(String(value.xml ?? ""));
    } catch (failure) {
      setError(failure);
    } finally {
      setStatementLoading(false);
    }
  }

  return (
    <Card style={{ minWidth: 0, maxWidth: "100%" }}>
      <Form layout="vertical" style={{ minWidth: 0 }}>
        <Form.Item label="XML do lote">
          <XmlTextArea value={xml} onChange={setXml} />
        </Form.Item>
        <Form.Item label="Cenário">
          <Select aria-label="Cenário" value={scenario} options={scenarios} onChange={setScenario} />
        </Form.Item>
        <Form.Item label="Tentativa">
          <InputNumber aria-label="Tentativa" min={1} value={attempt} onChange={(value) => setAttempt(value ?? 1)} />
        </Form.Item>
        <Button type="primary" loading={loading} disabled={!xml.trim()} onClick={submit}>Enviar lote simulado</Button>
        {loading && <Spin aria-label="Enviando lote" style={{ display: "block", marginBlock: token.margin }} />}
        {error !== null && <div style={{ marginBlockStart: token.margin }}><ErrorNotice error={error} /></div>}
        {result && (
          <Card
            title={result.aceito ? "Lote aceito" : "Lote não aceito"}
            style={{ width: "100%", minWidth: 0, marginBlockStart: token.margin }}
          >
            <Descriptions
              bordered
              column={1}
              items={[
                { key: "accepted", label: "Resultado", children: result.aceito ? "Aceito" : "Não aceito" },
                { key: "protocol", label: "Protocolo", children: result.numero_protocolo ?? result.protocolo ?? "—" },
                { key: "lot", label: "Número do lote", children: result.numero_lote ?? "—" },
                { key: "scenario", label: "Cenário", children: result.cenario },
              ]}
            />
            {!!result.findings.length && <FindingsTable findings={result.findings} />}
            {result.protocolo && (
              <Button loading={statementLoading} onClick={fetchStatement} style={{ marginBlockStart: token.margin }}>
                Consultar demonstrativo
              </Button>
            )}
            {statement && <pre className="notebook-output">{statement}</pre>}
          </Card>
        )}
        {!loading && !error && !result && (
          <Typography.Text type="secondary">Envie um lote para consultar o resultado simulado.</Typography.Text>
        )}
      </Form>
    </Card>
  );
}

export function Playground({
  errorExample,
  validExample,
}: {
  errorExample: string;
  validExample: string;
}) {
  const { token } = theme.useToken();
  const [apiKey, setApiKey] = useState("");
  const tabItems = [
    {
      key: "validate",
      label: "Validar",
      children: <ValidationTab apiKey={apiKey} errorExample={errorExample} validExample={validExample} />,
    },
    {
      key: "sandbox",
      label: "Operadora simulada",
      children: <SandboxTab apiKey={apiKey} validExample={validExample} />,
    },
  ];
  return (
    <>
      <Typography.Title>Playground TISS</Typography.Title>
      <Form layout="vertical">
        <Form.Item label="Chave">
          <Input.Password aria-label="Chave" value={apiKey} onChange={(event) => setApiKey(event.target.value)} autoComplete="off" />
        </Form.Item>
      </Form>
      <Tabs items={tabItems} style={{ minWidth: 0, maxWidth: "100%" }} />
      <Typography.Paragraph type="secondary" style={{ marginBlockStart: token.margin }}>
        Consulte <a href={`${site.url}/docs`}>a documentação</a> para conhecer as operações.
      </Typography.Paragraph>
    </>
  );
}
