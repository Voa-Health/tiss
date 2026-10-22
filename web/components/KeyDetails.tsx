"use client";

import { Alert, Button, Card, Descriptions, Flex, theme, Typography } from "antd";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  createMockCredentials,
  formatDateTime,
  keyLevelLabel,
  loginSimulationEnabled,
  site,
  type KeyCredentials,
} from "@/lib/site";

const refreshStorageKey = "voa-tiss.refresh";
const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";

type AuthError = "login_invalido" | "login_recusado";
type RenewalError = { message: string; needsLogin: boolean };

class RefreshFailure extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

function storedRefreshToken(): string {
  try {
    return window.sessionStorage.getItem(refreshStorageKey) ?? "";
  } catch {
    return "";
  }
}

function saveRefreshToken(value: string): void {
  try {
    if (value) window.sessionStorage.setItem(refreshStorageKey, value);
    else window.sessionStorage.removeItem(refreshStorageKey);
  } catch {}
}

function errorMessage(value: unknown): string {
  if (typeof value !== "object" || value === null || !("erro" in value)) return "";
  const error = value.erro;
  if (typeof error !== "object" || error === null || !("mensagem" in error)) return "";
  return typeof error.mensagem === "string" ? error.mensagem : "";
}

function isKeyCredentials(value: unknown): value is KeyCredentials {
  if (typeof value !== "object" || value === null) return false;
  return (
    "chave" in value &&
    typeof value.chave === "string" &&
    "refresh_token" in value &&
    typeof value.refresh_token === "string" &&
    "nivel" in value &&
    (value.nivel === "login" || value.nivel === "verified") &&
    "expira_em" in value &&
    typeof value.expira_em === "number" &&
    Number.isFinite(value.expira_em)
  );
}

async function requestRefresh(token: string): Promise<KeyCredentials> {
  const response = await fetch(`${apiBase}/v1/keys/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: token }),
  });
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new RefreshFailure(
      response.status,
      errorMessage(body) || "Não foi possível renovar a chave. Tente novamente.",
    );
  }
  if (!isKeyCredentials(body)) {
    throw new Error("Não foi possível renovar a chave. Tente novamente.");
  }
  return body;
}

export function KeyDetails() {
  const { token } = theme.useToken();
  const [key, setKey] = useState("");
  const [level, setLevel] = useState("");
  const [expires, setExpires] = useState<number | null>(null);
  const [refreshToken, setRefreshToken] = useState("");
  const [authError, setAuthError] = useState<AuthError | null>(null);
  const [renewalError, setRenewalError] = useState<RenewalError | null>(null);
  const [renewing, setRenewing] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const readOnce = useRef(false);

  useEffect(() => {
    if (readOnce.current) return;
    readOnce.current = true;
    const fragment = new URLSearchParams(window.location.hash.slice(1));
    setKey(fragment.get("chave") ?? "");
    setLevel(fragment.get("nivel") ?? "");
    const expiration = Number(fragment.get("expira_em"));
    setExpires(Number.isFinite(expiration) && expiration > 0 ? expiration : null);
    const error = fragment.get("erro");
    setAuthError(error === "login_invalido" || error === "login_recusado" ? error : null);
    const receivedToken = fragment.get("refresh_token");
    if (receivedToken !== null) saveRefreshToken(receivedToken);
    const nextRefreshToken = receivedToken ?? storedRefreshToken();
    setRefreshToken(nextRefreshToken);
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
    setLoaded(true);
  }, []);

  async function renew() {
    if (!refreshToken || renewing) return;
    setRenewing(true);
    setRenewalError(null);
    try {
      const credentials = loginSimulationEnabled()
        ? createMockCredentials()
        : await requestRefresh(refreshToken);
      setKey(credentials.chave);
      setLevel(credentials.nivel);
      setExpires(credentials.expira_em);
      setRefreshToken(credentials.refresh_token);
      saveRefreshToken(credentials.refresh_token);
    } catch (error) {
      if (error instanceof RefreshFailure && error.status === 401) {
        saveRefreshToken("");
        setRefreshToken("");
        setKey("");
        setLevel("");
        setExpires(null);
        setRenewalError({ message: "Entre novamente com a conta Voa.", needsLogin: true });
      } else {
        setRenewalError({
          message: error instanceof RefreshFailure
            ? error.message
            : "Não foi possível renovar a chave. Tente novamente.",
          needsLogin: false,
        });
      }
    } finally {
      setRenewing(false);
    }
  }

  if (!loaded) return <Card loading />;
  if (authError) {
    const message = authError === "login_invalido"
      ? "Não foi possível concluir o login. Tente novamente."
      : "O acesso não foi autorizado na conta Voa.";
    return (
      <Card>
        <Flex vertical align="flex-start" gap={token.margin}>
          <Alert type="error" showIcon title={message} />
          <Button type="primary" href="/entrar">Entrar novamente</Button>
        </Flex>
      </Card>
    );
  }
  if (!key && !refreshToken && renewalError?.needsLogin) {
    return (
      <Card>
        <Flex vertical align="flex-start" gap={token.margin}>
          <Alert type="error" showIcon title={renewalError.message} />
          <Button type="primary" href="/entrar">Entrar com Voa</Button>
        </Flex>
      </Card>
    );
  }
  if (!key && refreshToken) {
    return (
      <Card>
        <Flex vertical align="flex-start" gap={token.margin}>
          <Typography.Title level={2}>Renovar chave de acesso</Typography.Title>
          <Typography.Paragraph>Gere uma nova chave para continuar usando a API.</Typography.Paragraph>
          {renewalError && (
            <Alert
              type="error"
              showIcon
              title={renewalError.message}
              description={renewalError.needsLogin
                ? <Link href="/entrar">Entre com Voa novamente.</Link>
                : undefined}
            />
          )}
          <Button type="primary" loading={renewing} onClick={renew}>Renovar</Button>
        </Flex>
      </Card>
    );
  }
  if (!key) {
    return (
      <EmptyState
        title="Nenhuma chave recebida"
        description="Entre com Voa para obter uma chave de acesso."
        action={<Button type="primary" href="/entrar">Entrar com Voa</Button>}
      />
    );
  }

  const levelLabel = level === "verified" || level === "login" ? keyLevelLabel(level) : "Acesso";
  const expiresLabel = expires !== null
    ? formatDateTime(expires)
    : "Não informada";

  return (
    <Card>
      <Typography.Title level={2}>Sua chave</Typography.Title>
      <Typography.Paragraph>
        <Typography.Text copyable={{ text: key }} code>{key}</Typography.Text>
      </Typography.Paragraph>
      <Alert
        type="warning"
        showIcon
        title="Guarde a chave agora; ela não será exibida de novo."
        style={{ marginBlockEnd: token.margin }}
      />
      <Descriptions
        bordered
        column={1}
        items={[
          { key: "level", label: "Nível", children: levelLabel },
          { key: "expiry", label: "Validade", children: expiresLabel },
        ]}
      />
      <Flex
        vertical
        align="flex-start"
        gap={token.margin}
        style={{ marginBlockStart: token.marginLG }}
      >
        {renewalError && (
          <Alert
            type="error"
            showIcon
            title={renewalError.message}
            description={renewalError.needsLogin
              ? <Link href="/entrar">Entre com Voa novamente.</Link>
              : undefined}
          />
        )}
        {refreshToken ? (
          <Button type="primary" loading={renewing} onClick={renew}>Renovar</Button>
        ) : (
          <Button type="primary" href="/entrar">Obter nova chave</Button>
        )}
        <Link href={site.docsUrl}>Consultar documentação</Link>
      </Flex>
    </Card>
  );
}
