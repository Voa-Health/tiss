"use client";

import { Alert, Flex, Skeleton, theme } from "antd";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  chaveDoEvento,
  conteudoDoEvento,
  eventoTratado,
  lerAprovacaoPendente,
  lerAprovacaoResolvida,
  textoDaResposta,
  type AprovacaoPendente,
  type Envelope,
  type FalaDoHistorico,
} from "@/lib/chat/protocolo";
import { ligarChat, type CredencialDoChat, type FalhaDoChat, type LigacaoDoChat } from "@/lib/chat/transporte";
import { CorpoDaConversa } from "./CorpoDaConversa";

type RespostaInicial = {
  chat_id: string | null;
  falas: FalaDoHistorico[];
  codigo?: string;
  erro?: string;
};

type Fala = FalaDoHistorico & { id: string };

async function lerResposta(resposta: Response): Promise<RespostaInicial> {
  const dados = await resposta.json().catch(() => ({})) as RespostaInicial;
  if (!resposta.ok) {
    const erro = new Error(dados.erro || "Não foi possível abrir o Assistente.") as Error & { code?: string };
    erro.code = dados.codigo;
    throw erro;
  }
  return dados;
}

export function Conversa({ podeDecidir }: { podeDecidir: boolean }) {
  const { token } = theme.useToken();
  const ligacao = useRef<LigacaoDoChat | null>(null);
  const respostaEmCurso = useRef("");
  const proximoId = useRef(0);
  const [falas, setFalas] = useState<Fala[]>([]);
  const [resposta, setResposta] = useState("");
  const [chatId, setChatId] = useState<string | null>(null);
  const [aprovacao, setAprovacao] = useState<AprovacaoPendente | null>(null);
  const [conectada, setConectada] = useState(false);
  const [trabalhando, setTrabalhando] = useState(false);
  const [atividade, setAtividade] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [carregandoDecisao, setCarregandoDecisao] = useState(false);
  const [falha, setFalha] = useState<FalhaDoChat | null>(null);
  const [configAusente, setConfigAusente] = useState(false);
  const [ignorados, setIgnorados] = useState<string[]>([]);

  const adicionarFala = useCallback((papel: FalaDoHistorico["papel"], texto: string) => {
    proximoId.current += 1;
    setFalas((anteriores) => [...anteriores, { id: String(proximoId.current), papel, texto }]);
  }, []);

  const finalizarResposta = useCallback(() => {
    const texto = respostaEmCurso.current;
    if (texto) adicionarFala("analista", texto);
    respostaEmCurso.current = "";
    setResposta("");
    setTrabalhando(false);
  }, [adicionarFala]);

  const receberEvento = useCallback((envelope: Envelope) => {
    const tipo = chaveDoEvento(envelope);
    if (tipo === "response") {
      const trecho = textoDaResposta(envelope);
      if (trecho) {
        respostaEmCurso.current += trecho;
        setResposta(respostaEmCurso.current);
      }
      return;
    }
    if (tipo === "custom:tool-call-start") {
      setTrabalhando(true);
      setAtividade("O Assistente está consultando as regras.");
      return;
    }
    if (tipo === "custom:tool-call-end") {
      setAtividade("Consulta concluída.");
      return;
    }
    if (tipo === "run-accepted" || tipo === "stream-start") {
      setTrabalhando(true);
      return;
    }
    if (tipo === "custom:turn-finalized" || tipo === "stream-end") {
      finalizarResposta();
      setAtividade(null);
      return;
    }
    if (tipo === "error") {
      const conteudo = conteudoDoEvento(envelope);
      setFalha({
        codigo: typeof conteudo.code === "string" ? conteudo.code : "erro_no_turno",
        mensagem: typeof conteudo.message === "string" ? conteudo.message : "Não foi possível concluir a conversa.",
      });
      finalizarResposta();
      return;
    }
    if (tipo === "custom:hitl-pending") {
      const pendente = lerAprovacaoPendente(envelope);
      if (pendente) setAprovacao(pendente);
      return;
    }
    if (tipo === "custom:hitl-resolved") {
      const resolvida = lerAprovacaoResolvida(envelope);
      if (resolvida) {
        setAprovacao((atual) => atual?.correlation_id === resolvida.correlation_id ? null : atual);
        setCarregandoDecisao(false);
        window.dispatchEvent(new Event("tiss:regras-atualizadas"));
      }
      return;
    }
    if (!eventoTratado(envelope)) {
      setIgnorados((anteriores) => anteriores.includes(tipo) ? anteriores : [...anteriores, tipo]);
    }
  }, [finalizarResposta]);

  useEffect(() => {
    let ativa = true;
    const iniciar = async () => {
      try {
        let inicial = await lerResposta(await fetch("/api/conversa?historico=1", { cache: "no-store" }));
        if (!inicial.chat_id) {
          const criada = await fetch("/api/conversa", { method: "POST", cache: "no-store" });
          await lerResposta(criada);
          inicial = await lerResposta(await fetch("/api/conversa?historico=1", { cache: "no-store" }));
        }
        if (!ativa || !inicial.chat_id) return;
        setChatId(inicial.chat_id);
        const historico = inicial.falas ?? [];
        setFalas(historico.map((fala, indice) => ({ ...fala, id: `historico-${indice}` })));
        proximoId.current = historico.length;
        const conexao = ligarChat({
          chatId: inicial.chat_id,
          async carregarCredencial(signal): Promise<CredencialDoChat> {
            const resposta = await fetch("/api/conversa", { cache: "no-store", signal });
            const dados = await lerResposta(resposta) as RespostaInicial & CredencialDoChat;
            if (!dados.token || !dados.socket || !dados.profile || dados.chat_id !== inicial.chat_id) {
              throw new Error("Credencial de conversa inválida.");
            }
            return {
              token: dados.token,
              socket: dados.socket,
              chat_id: dados.chat_id,
              profile: dados.profile,
            };
          },
          aoEvento: receberEvento,
          aoEstado: (valor) => ativa && setConectada(valor),
          aoFalha: (valor) => {
            if (ativa) setFalha(valor);
          },
        });
        ligacao.current = conexao;
      } catch (erro) {
        if (!ativa) return;
        const motivo = erro instanceof Error ? erro : new Error("Não foi possível abrir o Assistente.");
        const codigo = "code" in motivo && typeof motivo.code === "string" ? motivo.code : "";
        setConfigAusente(codigo === "configuracao_ausente");
        const proximaFalha = { codigo: codigo || "abertura_indisponivel", mensagem: motivo.message };
        setFalha(proximaFalha);
      } finally {
        if (ativa) setCarregando(false);
      }
    };
    void iniciar();
    return () => {
      ativa = false;
      ligacao.current?.fechar();
      ligacao.current = null;
    };
  }, [receberEvento]);

  function enviar(texto: string) {
    setFalha(null);
    adicionarFala("pessoa", texto);
    setTrabalhando(true);
    ligacao.current?.enviar(texto);
  }

  function resolver(pendente: AprovacaoPendente, aprovada: boolean, motivo?: string) {
    if (!ligacao.current) return;
    setCarregandoDecisao(true);
    ligacao.current.resolver(pendente, aprovada, motivo);
  }

  if (carregando) return <Skeleton active paragraph={{ rows: 4 }} />;
  if (configAusente) {
    return <Alert type="warning" showIcon title="Assistente indisponível neste ambiente" />;
  }

  return (
    <Flex vertical gap={token.marginSM} style={{ flex: 1, minHeight: 0 }}>
      {chatId && (
        <CorpoDaConversa
          falas={falas}
          resposta={resposta}
          aprovacao={aprovacao}
          erro={falha?.mensagem ?? null}
          atividade={atividade}
          podeDecidir={podeDecidir}
          ignorados={ignorados}
          conectada={conectada}
          trabalhando={trabalhando}
          carregandoDecisao={carregandoDecisao}
          aoEnviar={enviar}
          aoResolver={resolver}
          aoReconectar={() => ligacao.current?.reconectar()}
        />
      )}
      {!chatId && falha && <Alert type="error" showIcon title={falha.mensagem} />}
    </Flex>
  );
}
