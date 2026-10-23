import {
  analisarEnvelope,
  quadroDeEnvio,
  quadroDeResolucao,
  type AprovacaoPendente,
  type Envelope,
} from "./protocolo";

export type CredencialDoChat = {
  token: string;
  socket: string;
  chat_id: string;
  profile: string;
};

export type FalhaDoChat = {
  mensagem: string;
  codigo: string;
};

export type LigacaoDoChat = {
  enviar(texto: string): void;
  resolver(aprovacao: AprovacaoPendente, aprovada: boolean, motivo?: string): void;
  reconectar(): void;
  fechar(): void;
};

export type AparelhagemDoChat = {
  chatId: string;
  carregarCredencial(signal: AbortSignal): Promise<CredencialDoChat>;
  aoEvento(envelope: Envelope): void;
  aoEstado(conectado: boolean): void;
  aoFalha(falha: FalhaDoChat | null): void;
};

const MAXIMO_DE_TENTATIVAS = 5;

export function ligarChat(aparelhagem: AparelhagemDoChat): LigacaoDoChat {
  let socket: WebSocket | null = null;
  let encerrado = false;
  let tentativas = 0;
  let retorno: ReturnType<typeof setTimeout> | null = null;
  let abortador: AbortController | null = null;
  let perfil = "";
  const fila: unknown[] = [];

  function enviarQuadro(quadro: unknown) {
    if (encerrado) return;
    if (socket?.readyState === WebSocket.OPEN) {
      try {
        socket.send(JSON.stringify(quadro));
        return;
      } catch {
        fila.push(quadro);
        socket.close();
        return;
      }
    }
    fila.push(quadro);
  }

  async function conectar() {
    if (encerrado) return;
    abortador?.abort();
    abortador = new AbortController();
    aparelhagem.aoEstado(false);
    try {
      const credencial = await aparelhagem.carregarCredencial(abortador.signal);
      if (encerrado || abortador.signal.aborted) return;
      if (!credencial.token || !credencial.socket || credencial.chat_id !== aparelhagem.chatId) {
        throw new Error("Credencial de conversa inválida.");
      }
      perfil = credencial.profile;
      const token = credencial.token;
      const novoSocket = new WebSocket(credencial.socket, ["Authorization", token]);
      socket = novoSocket;
      novoSocket.onopen = () => {
        if (encerrado || socket !== novoSocket) return;
        tentativas = 0;
        aparelhagem.aoEstado(true);
        aparelhagem.aoFalha(null);
        while (fila.length) {
          novoSocket.send(JSON.stringify(fila.shift()));
        }
      };
      novoSocket.onmessage = (evento) => {
        if (encerrado || socket !== novoSocket) return;
        let envelope: Envelope | null = null;
        try {
          envelope = analisarEnvelope(JSON.parse(String(evento.data)));
        } catch {
          return;
        }
        if (envelope) aparelhagem.aoEvento(envelope);
      };
      novoSocket.onclose = (evento) => {
        if (encerrado || socket !== novoSocket) return;
        socket = null;
        aparelhagem.aoEstado(false);
        tentativas += 1;
        if (tentativas >= MAXIMO_DE_TENTATIVAS) {
          aparelhagem.aoFalha({
            codigo: String(evento.code),
            mensagem: "A conexão foi interrompida. Tente reconectar.",
          });
          return;
        }
        retorno = setTimeout(() => {
          retorno = null;
          void conectar();
        }, Math.min(1_000 * 2 ** (tentativas - 1), 15_000));
      };
      novoSocket.onerror = () => {};
    } catch (erro) {
      if (encerrado || abortador.signal.aborted) return;
      tentativas += 1;
      aparelhagem.aoFalha({
        codigo: "conexao_indisponivel",
        mensagem: erro instanceof Error ? erro.message : "Não foi possível conectar ao Assistente.",
      });
      aparelhagem.aoEstado(false);
      if (tentativas < MAXIMO_DE_TENTATIVAS) {
        retorno = setTimeout(() => {
          retorno = null;
          void conectar();
        }, Math.min(1_000 * 2 ** (tentativas - 1), 15_000));
      }
    }
  }

  void conectar();
  return {
    enviar(texto) {
      enviarQuadro(quadroDeEnvio(aparelhagem.chatId, texto, perfil));
    },
    resolver(aprovacao, aprovada, motivo) {
      enviarQuadro(quadroDeResolucao(aparelhagem.chatId, aprovacao, aprovada, motivo));
    },
    reconectar() {
      if (encerrado) return;
      tentativas = 0;
      aparelhagem.aoFalha(null);
      if (retorno) clearTimeout(retorno);
      retorno = null;
      socket?.close();
      void conectar();
    },
    fechar() {
      encerrado = true;
      abortador?.abort();
      if (retorno) clearTimeout(retorno);
      retorno = null;
      const atual = socket;
      socket = null;
      if (atual) {
        atual.onopen = atual.onmessage = atual.onerror = atual.onclose = null;
        atual.close();
      }
    },
  };
}
