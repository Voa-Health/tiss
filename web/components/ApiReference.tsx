"use client";

import { Card, Descriptions, Divider, Flex, Tag, theme, Typography } from "antd";
import type { OpenApiDocument, OpenApiOperation, OpenApiSchema } from "@/lib/content";
import { operationAnchor } from "@/lib/site";

const operationDescriptions: Record<string, string> = {
  "/oauth/client.json": "Obter a configuração pública do cliente OAuth.",
  "/v1/auth/callback": "Concluir o login com a conta Voa.",
  "/v1/auth/login": "Iniciar o login com a conta Voa.",
  "/v1/keys/refresh": "Renovar uma chave de acesso usando o token de renovação.",
  "/v1/limits": "Consultar a configuração de uso da API.",
  "/v1/operadoras/{registro}/rede": "Listar os estabelecimentos da rede hospitalar de uma operadora.",
  "/v1/parse_demonstrativo": "Interpretar um demonstrativo de pagamento TISS.",
  "/v1/plan_reconciliation": "Planejar a conciliação entre guias e demonstrativos.",
  "/v1/rede": "Listar as operadoras que atendem um estabelecimento (CNPJ ou CNES).",
  "/v1/sadt_catalog": "Consultar os campos do catálogo SP/SADT.",
  "/v1/sadt_missing": "Identificar campos ausentes em uma guia SP/SADT.",
  "/v1/sandbox/lotes": "Enviar um lote à operadora simulada.",
  "/v1/sandbox/lotes/{protocolo}/demonstrativo": "Consultar o demonstrativo de um lote simulado.",
  "/v1/tuss_lookup": "Consultar um código TUSS.",
  "/v1/tuss_search": "Pesquisar códigos TUSS.",
  "/v1/validate": "Validar um lote TISS e retornar os achados.",
};

const generatedResponses: Record<string, string> = {
  "Successful Response": "Resposta bem-sucedida",
  "Validation Error": "Entrada inválida",
  "Internal Server Error": "Erro interno do serviço",
  "Not Found": "Recurso não encontrado",
};

function schemaProperties(schema?: OpenApiSchema) {
  return Object.entries(schema?.properties ?? {}).map(([name, property]) => ({
    key: name,
    label: name,
    children: (
      <>
        <code>{Array.isArray(property.type) ? property.type.join(" | ") : property.type ?? "objeto"}</code>
        {schema?.required?.includes(name) && <Tag color="red">obrigatório</Tag>}
        {property.enum && <div>Valores: {property.enum.join(", ")}</div>}
      </>
    ),
  }));
}

function operationDescription(path: string, operation: OpenApiOperation): string {
  return operation.description?.trim() || operationDescriptions[path] || "Operação HTTP da API.";
}

function responseDescription(status: string, description?: string): string {
  if (status === "200") return "Resposta bem-sucedida";
  if (status === "422") return "Entrada inválida";
  return (description && generatedResponses[description]) || description || "Resposta da operação.";
}

function OperationCard({
  path,
  method,
  operation,
}: {
  path: string;
  method: string;
  operation: OpenApiOperation;
}) {
  const { token } = theme.useToken();
  const requestSchema = Object.values(operation.requestBody?.content ?? {})
    .map((entry) => entry.schema)
    .find((schema) => schema?.properties);
  const anchor = operationAnchor(method, path);

  return (
    <Card id={anchor} style={{ scrollMarginTop: token.marginLG }}>
      <Typography.Title level={3}>
        <Tag color={method === "GET" ? "blue" : "purple"}>{method}</Tag>
        <code>{path}</code>
      </Typography.Title>
      {operation.tags?.map((tag) => <Tag key={tag}>{tag}</Tag>)}
      <Typography.Title level={4}>{operationDescription(path, operation)}</Typography.Title>
      {requestSchema && (
        <>
          <Typography.Title level={5}>Corpo da solicitação</Typography.Title>
          <Descriptions bordered size="small" column={1} items={schemaProperties(requestSchema)} />
        </>
      )}
      {operation.responses && (
        <>
          <Typography.Title level={5}>Respostas</Typography.Title>
          <Descriptions
            bordered
            size="small"
            column={1}
            items={Object.entries(operation.responses).map(([status, response]) => ({
              key: status,
              label: status,
              children: responseDescription(status, response.description),
            }))}
          />
        </>
      )}
    </Card>
  );
}

export function ApiReference({ api }: { api: OpenApiDocument }) {
  const { token } = theme.useToken();
  const operations = Object.entries(api.paths).flatMap(([path, methods]) =>
    Object.entries(methods)
      .filter(([method]) => ["get", "post", "put", "patch", "delete"].includes(method))
      .map(([method, operation]) => ({ path, method: method.toUpperCase(), operation })),
  ).sort(
    (first, second) =>
      Number(first.path.startsWith("/oauth/")) - Number(second.path.startsWith("/oauth/")) ||
      first.path.localeCompare(second.path) ||
      first.method.localeCompare(second.method),
  );
  return (
    <>
      <Typography.Title>Referência da API</Typography.Title>
      <Typography.Paragraph>
        A API também oferece o endpoint MCP <code>/mcp</code>. Envie a chave no cabeçalho{" "}
        <code>Authorization: Bearer &lt;chave&gt;</code>.
      </Typography.Paragraph>
      <Divider />
      <Card title="Operações" style={{ marginBlockEnd: token.marginLG }}>
        <Flex wrap gap={token.marginXS}>
          {operations.map(({ path, method }) => (
            <Typography.Link
              key={`${method}:${path}`}
              href={`#${operationAnchor(method, path)}`}
              style={{ display: "inline-flex", alignItems: "center", gap: token.marginXXS }}
            >
              <Tag color={method === "GET" ? "blue" : "purple"}>{method}</Tag>
              <code>{path}</code>
            </Typography.Link>
          ))}
        </Flex>
      </Card>
      {operations.map(({ path, method, operation }) => (
        <div key={`${method}:${path}`} style={{ marginBlockEnd: token.marginLG }}>
          <OperationCard path={path} method={method} operation={operation} />
        </div>
      ))}
    </>
  );
}
