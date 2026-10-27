"use client";

import { App, Alert, Button, Card, Descriptions, Divider, Flex, List, Modal, Skeleton, Space, Tag, Typography, theme } from "antd";
import Link from "next/link";
import { useEffect, useState } from "react";
import { dataHora } from "@/lib/org/formato";
import { FalhaDoPedido, pedir, useRecurso } from "@/lib/org/cliente";
import { montarLinkOficial } from "@/lib/org/regras";
import type { EstadoDaOrg } from "@/lib/org/tipos";
import type { EstadoDasRegras, PayloadDoLinkOficial, RegraTiss, VersoesDasRegras } from "@/lib/org/tiss";
import { hrefDaOrg } from "./secoes";

function nomeDaRegra(regra: RegraTiss): string {
  return String(regra.nome ?? regra.id ?? "Regra sem identificação");
}

export function RulesSection({ org }: { org: EstadoDaOrg }) {
  const { token } = theme.useToken();
  const { message } = App.useApp();
  const estado = useRecurso<EstadoDasRegras>(`org/${org.id}/tiss/rules/`);
  const versoes = useRecurso<VersoesDasRegras>(`org/${org.id}/tiss/rules/versions/`);
  const [publicando, setPublicando] = useState(false);
  const [buscandoLink, setBuscandoLink] = useState(false);
  const [link, setLink] = useState<ReturnType<typeof montarLinkOficial> | null>(null);
  const pacote = estado.dados;
  const validacao = pacote?.validation;
  const diferenca = pacote?.diff;
  const podePublicar = org.is_admin || org.my_areas.includes("administration");
  const recarregarEstado = estado.recarregar;
  const recarregarVersoes = versoes.recarregar;

  useEffect(() => {
    const atualizar = () => {
      recarregarEstado();
      recarregarVersoes();
    };
    window.addEventListener("tiss:regras-atualizadas", atualizar);
    return () => window.removeEventListener("tiss:regras-atualizadas", atualizar);
  }, [recarregarEstado, recarregarVersoes]);

  async function publicar() {
    setPublicando(true);
    try {
      await pedir(`org/${org.id}/tiss/rules/publish/`, { method: "POST" });
      message.success("Versão publicada.");
      estado.recarregar();
      versoes.recarregar();
    } catch (erro) {
      message.error(erro instanceof Error ? erro.message : "Não foi possível publicar.");
    } finally {
      setPublicando(false);
    }
  }

  async function prepararLink() {
    if (!pacote?.published) return;
    setBuscandoLink(true);
    try {
      const dados = await pedir<PayloadDoLinkOficial>(
        `org/${org.id}/tiss/rules/official-pr/?version=${pacote.published.version}`,
      );
      setLink(montarLinkOficial(dados));
    } catch (erro) {
      message.error(erro instanceof FalhaDoPedido ? erro.message : "Não foi possível preparar o conteúdo público.");
    } finally {
      setBuscandoLink(false);
    }
  }

  if (estado.carregando || versoes.carregando) return <Skeleton active />;
  if (estado.erro || versoes.erro) {
    const erro = estado.erro ?? versoes.erro;
    return <Alert type="error" showIcon title="Não foi possível carregar as regras." description={erro?.message} />;
  }

  const regras = Array.isArray(pacote?.draft?.content.regras) ? pacote.draft.content.regras as RegraTiss[] : [];
  const diferencaContagens = [
    { chave: "Adicionadas", total: diferenca?.added.length ?? 0 },
    { chave: "Removidas", total: diferenca?.removed.length ?? 0 },
    { chave: "Alteradas", total: diferenca?.changed.length ?? 0 },
  ];

  return (
    <>
      <Flex vertical gap={token.margin}>
        <Alert
          type="info"
          showIcon
          title="O agente propõe; a Auditoria decide. Publicar é sempre uma ação humana da Administração."
          description={!podePublicar ? "A edição do rascunho acontece na conversa com o Assistente." : undefined}
        />
        <Card title="Rascunho">
          {pacote?.draft ? (
            <Flex vertical gap={token.margin}>
              <Descriptions
                size="small"
                column={1}
                items={[
                  { key: "status", label: "Estado", children: pacote.draft.status === "draft" ? "Rascunho" : pacote.draft.status },
                  { key: "atualizado", label: "Atualizado", children: dataHora(pacote.draft.updated_at) },
                  { key: "regras", label: "Regras", children: regras.length },
                ]}
              />
              {validacao && (
                <Alert
                  type={validacao.valid ? "success" : "error"}
                  showIcon
                  title={validacao.valid ? "Pacote válido" : "A validação encontrou pendências."}
                  description={
                    validacao.errors.length > 0 ? (
                      <List
                        size="small"
                        dataSource={validacao.errors}
                        renderItem={(erro) => <List.Item>{erro}</List.Item>}
                      />
                    ) : undefined
                  }
                />
              )}
              {validacao?.rules_without_source.length ? (
                <Alert
                  type="warning"
                  showIcon
                  title={`Regras sem fonte: ${validacao.rules_without_source.join(", ")}`}
                />
              ) : null}
              <List
                size="small"
                header={<Typography.Text strong>Regras do pacote</Typography.Text>}
                dataSource={regras}
                renderItem={(regra) => (
                  <List.Item>
                    <Typography.Text>{nomeDaRegra(regra)}</Typography.Text>
                    {!regra.source && <Tag color="warning">Fonte ausente</Tag>}
                  </List.Item>
                )}
              />
            </Flex>
          ) : (
            <Typography.Text type="secondary">Ainda não há rascunho.</Typography.Text>
          )}
        </Card>
        <Space wrap>
          {podePublicar ? (
            <>
              <Button
                type="primary"
                disabled={!validacao?.valid || !pacote?.draft}
                loading={publicando}
                onClick={() => void publicar()}
              >
                Publicar
              </Button>
              <Button
                loading={buscandoLink}
                disabled={!pacote?.published}
                onClick={() => void prepararLink()}
              >
                Abrir proposta pública (Oficial)
              </Button>
            </>
          ) : (
            <Link href={hrefDaOrg(org.id, "regras", true)}>Abrir Assistente</Link>
          )}
        </Space>
        {podePublicar && (
          <Typography.Text type="secondary">
            Abre no GitHub o arquivo da versão publicada para você revisar e enviar a proposta ao repositório público. Nenhum token sai deste site.
          </Typography.Text>
        )}

        <Card title="Diferenças em relação à versão publicada">
          <Flex vertical gap={token.marginSM}>
            <Space wrap>
              {diferencaContagens.map(({ chave, total }) => <Tag key={chave}>{chave}: {total}</Tag>)}
            </Space>
            {diferenca && (
              <Descriptions
                size="small"
                column={1}
                items={[
                  { key: "novas", label: "Novas", children: diferenca.added.map((regra) => regra.id).join(", ") || "—" },
                  { key: "removidas", label: "Removidas", children: diferenca.removed.map((regra) => regra.id).join(", ") || "—" },
                  { key: "alteradas", label: "Alteradas", children: diferenca.changed.map((regra) => regra.id).join(", ") || "—" },
                ]}
              />
            )}
          </Flex>
        </Card>

        <Card title="Versões publicadas">
          <List
            dataSource={versoes.dados?.items ?? []}
            locale={{ emptyText: "Nenhuma versão publicada." }}
            renderItem={(versao) => (
              <List.Item key={versao.id}>
                <Flex wrap justify="space-between" gap={token.margin}>
                  <Typography.Text strong>Versão {versao.version}</Typography.Text>
                  <Typography.Text type="secondary">{dataHora(versao.published_at)}</Typography.Text>
                </Flex>
              </List.Item>
            )}
          />
        </Card>
      </Flex>
      <Modal
        open={Boolean(link)}
        title={link?.titulo}
        onCancel={() => setLink(null)}
        footer={link ? (
          <Button type="primary" href={link.url} target="_blank" rel="noopener noreferrer">
            Abrir no GitHub
          </Button>
        ) : null}
      >
        {link && (
          <Flex vertical gap={token.marginSM}>
            <Typography.Paragraph copyable>{link.titulo}</Typography.Paragraph>
            <Typography.Paragraph copyable>{link.corpo}</Typography.Paragraph>
            {link.conteudoNoModal && (
              <>
                <Divider />
                <Typography.Paragraph type="secondary">
                  O conteúdo é longo para a URL e pode ser copiado para o formulário público.
                </Typography.Paragraph>
                <Typography.Paragraph copyable code style={{ maxHeight: 240, overflow: "auto" }}>
                  {link.conteudo}
                </Typography.Paragraph>
              </>
            )}
          </Flex>
        )}
      </Modal>
    </>
  );
}
