import { analisarEnvelope, leitorSse, type Envelope } from "./protocolo";

export type FalhaDoChat = {
  mensagem: string;
  codigo: string;
};

export type LigacaoDoChat = {
  /** Resolve quando a resposta termina; devolve o corpo do turno sem resposta. */
  turno(corpo: Record<string, unknown>): Promise<Record<string, unknown> | null>;
  reconectar(): void;
  fechar(): void;
};

export type AparelhagemDoChat = {
  /** `/api/conversa/<org>/<chat>` */
  base: string;
  aoEvento(envelope: Envelope): void;
  aoEstado(conectado: boolean): void;
  aoFalha(falha: FalhaDoChat | null): void;
};

const MAXIMO_DE_TENTATIVAS = 5;
const FIM = new Set(["stream-end", "stream-expired"]);

type Corrida = { runId: string | null; cursor: string | null; terminou: boolean };

function objeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

async function corpoJson(resposta: Response): Promise<Record<string, unknown>> {
  const corpo: unknown = await resposta.json().catch(() => null);
  return objeto(corpo) ? corpo : {};
}

function falhaDaResposta(status: number, corpo: Record<string, unknown>): FalhaDoChat {
  const texto = [corpo.detail, corpo.erro].find((valor): valor is string => typeof valor === "string");
  const codigo = [corpo.code, corpo.codigo].find((valor): valor is string => typeof valor === "string");
  return { codigo: codigo ?? `http_${status}`, mensagem: texto ?? "Não foi possível falar com o Assistente." };
}

const esperar = (ms: number, signal: AbortSignal) =>
  new Promise<void>((resolve) => {
    const relogio = setTimeout(resolve, ms);
    signal.addEventListener("abort", () => {
      clearTimeout(relogio);
      resolve();
    }, { once: true });
  });

export function ligarChat(aparelhagem: AparelhagemDoChat): LigacaoDoChat {
  const abortador = new AbortController();
  let pendente: Corrida | null = null;

  async function ler(resposta: Response, corrida: Corrida) {
    if (!resposta.body) return;
    const leitor = resposta.body.getReader();
    const decodificador = new TextDecoder();
    const alimentar = leitorSse(({ id, evento, dados }) => {
      if (id) corrida.cursor = id;
      let valor: unknown;
      try {
        valor = JSON.parse(dados);
      } catch {
        return;
      }
      if (evento === "turn-accepted") {
        if (objeto(valor) && typeof valor.run_id === "string") corrida.runId = valor.run_id;
        return;
      }
      const envelope = analisarEnvelope(valor);
      if (!envelope) return;
      if (FIM.has(envelope.event_type ?? "")) corrida.terminou = true;
      aparelhagem.aoEvento(envelope);
    });
    while (!corrida.terminou) {
      const { value, done } = await leitor.read();
      if (done) break;
      alimentar(decodificador.decode(value, { stream: true }));
    }
    if (corrida.terminou) leitor.cancel().catch(() => undefined);
  }

  async function seguir(corrida: Corrida) {
    pendente = corrida;
    for (let tentativa = 1; !corrida.terminou && corrida.runId; tentativa += 1) {
      if (tentativa > MAXIMO_DE_TENTATIVAS) {
        aparelhagem.aoFalha({ codigo: "conexao_interrompida", mensagem: "A conexão foi interrompida. Tente reconectar." });
        return;
      }
      aparelhagem.aoEstado(false);
      await esperar(Math.min(1_000 * 2 ** (tentativa - 1), 15_000), abortador.signal);
      if (abortador.signal.aborted) return;
      try {
        const resposta = await fetch(`${aparelhagem.base}/runs/${corrida.runId}`, {
          headers: corrida.cursor ? { "last-event-id": corrida.cursor } : undefined,
          cache: "no-store",
          signal: abortador.signal,
        });
        if (resposta.status === 404 || resposta.status === 409) {
          aparelhagem.aoFalha(falhaDaResposta(resposta.status, await corpoJson(resposta)));
          corrida.terminou = true;
          break;
        }
        if (resposta.ok) {
          aparelhagem.aoEstado(true);
          const antes = corrida.cursor;
          await ler(resposta, corrida);
          if (corrida.cursor !== antes) tentativa = 0;
        }
      } catch {
        if (abortador.signal.aborted) return;
      }
    }
    pendente = null;
    aparelhagem.aoEstado(true);
  }

  return {
    async turno(corpo) {
      aparelhagem.aoFalha(null);
      const corrida: Corrida = { runId: null, cursor: null, terminou: false };
      try {
        const resposta = await fetch(`${aparelhagem.base}/turnos`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(corpo),
          cache: "no-store",
          signal: abortador.signal,
        });
        if (!resposta.ok) {
          aparelhagem.aoFalha(falhaDaResposta(resposta.status, await corpoJson(resposta)));
          return null;
        }
        if (!(resposta.headers.get("content-type") ?? "").includes("text/event-stream")) return corpoJson(resposta);
        await ler(resposta, corrida);
      } catch {
        if (abortador.signal.aborted) return null;
        if (!corrida.runId) {
          aparelhagem.aoFalha({ codigo: "conexao_indisponivel", mensagem: "Não foi possível falar com o Assistente." });
          return null;
        }
      }
      if (!corrida.terminou) await seguir(corrida);
      return null;
    },
    reconectar() {
      aparelhagem.aoFalha(null);
      if (pendente && !pendente.terminou) void seguir(pendente);
      else aparelhagem.aoEstado(true);
    },
    fechar() {
      abortador.abort();
    },
  };
}
