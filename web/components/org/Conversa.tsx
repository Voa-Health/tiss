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
  turnoDeEnvio,
  turnoDeResolucao,
  type AprovacaoPendente,
  type Envelope,
  type FalaDoHistorico,
} from "@/lib/chat/protocolo";
import { ligarChat, type FalhaDoChat, type LigacaoDoChat } from "@/lib/chat/transporte";
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

export function Conversa({ orgId, podeDecidir }: { orgId: string; podeDecidir: boolean }) {
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

  const concluirAprovacao = useCallback((correlationId: string) => {
    setAprovacao((atual) => atual?.correlation_id === correlationId ? null : atual);
    setCarregandoDecisao(false);
    window.dispatchEvent(new Event("tiss:regras-atualizadas"));
  }, []);

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
    if (tipo === "stream-start") {
      setTrabalhando(true);
      return;
    }
    if (tipo === "custom:turn-finalized" || tipo === "stream-end" || tipo === "stream-expired") {
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
      if (resolvida) concluirAprovacao(resolvida.correlation_id);
      return;
    }
    if (!eventoTratado(envelope)) {
      setIgnorados((anteriores) => anteriores.includes(tipo) ? anteriores : [...anteriores, tipo]);
    }
  }, [concluirAprovacao, finalizarResposta]);

  useEffect(() => {
    let ativa = true;
    const base = `/api/conversa/${orgId}`;
    const iniciar = async () => {
      try {
        const inicial = await lerResposta(await fetch(base, { cache: "no-store" }));
        const id = inicial.chat_id ?? (await lerResposta(await fetch(base, { method: "POST", cache: "no-store" }))).chat_id;
        if (!ativa || !id) return;
        setChatId(id);
        const historico = inicial.chat_id ? inicial.falas ?? [] : [];
        setFalas(historico.map((fala, indice) => ({ ...fala, id: `historico-${indice}` })));
        proximoId.current = historico.length;
        ligacao.current = ligarChat({
          base: `${base}/${id}`,
          aoEvento: receberEvento,
          aoEstado: (valor) => ativa && setConectada(valor),
          aoFalha: (valor) => {
            if (ativa) setFalha(valor);
          },
        });
        setConectada(true);
      } catch (erro) {
        if (!ativa) return;
        const motivo = erro instanceof Error ? erro : new Error("Não foi possível abrir o Assistente.");
        const codigo = "code" in motivo && typeof motivo.code === "string" ? motivo.code : "";
        setConfigAusente(codigo === "configuracao_ausente");
        setFalha({ codigo: codigo || "abertura_indisponivel", mensagem: motivo.message });
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
  }, [orgId, receberEvento]);

  function enviar(texto: string) {
    adicionarFala("pessoa", texto);
    setTrabalhando(true);
    void ligacao.current?.turno(turnoDeEnvio(texto)).finally(() => {
      finalizarResposta();
      setAtividade(null);
    });
  }

  function resolver(pendente: AprovacaoPendente, aprovada: boolean, motivo?: string) {
    if (!ligacao.current) return;
    setCarregandoDecisao(true);
    void ligacao.current
      .turno(turnoDeResolucao(pendente, aprovada, motivo))
      .then((corpo) => {
        if (corpo?.resolved) concluirAprovacao(pendente.correlation_id);
      })
      .finally(() => {
        setCarregandoDecisao(false);
        finalizarResposta();
      });
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
