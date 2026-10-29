"use client";

import {
  AppstoreOutlined,
  CodeOutlined,
  ExperimentOutlined,
  GlobalOutlined,
  MedicineBoxOutlined,
  SafetyCertificateOutlined,
  ShopOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Alert, AutoComplete, Button, Card, Checkbox, Col, Flex, Form, Input, Row, Select, theme, Typography } from "antd";
import Image from "next/image";
import Link from "next/link";
import { type ReactNode, useRef, useState } from "react";
import {
  caminhoDaBusca,
  chaveDaBusca,
  lerResposta,
  nomeSugerido,
  rotuloDaUnidade,
  situacaoDaBusca,
  type ChaveDaBusca,
  type Situacao,
} from "@/lib/org/busca";
import { abrirDeNovo, FalhaDoPedido, pedir } from "@/lib/org/cliente";
import type { CatalogoDeOrgs, EstadoDaOrg, Subtipo } from "@/lib/org/tipos";
import { sair } from "./OrgCasca";
import { hrefDaOrg, ROTULO_DO_TIPO } from "./secoes";

type Campos = {
  destino: string;
  name?: string;
  subtype: string;
  cnpj: string;
  registro_ans?: string;
  cnes?: string;
  aceite: boolean;
};

const NOVA = "nova";

const EM_USO = /pertence a outra organização/i;

const textoDaChave = (chave: ChaveDaBusca | null) => (chave ? `${chave.campo}:${chave.valor}` : "");

function AvisoDaBusca({ situacao, nomeAtual, aoUsarNome }: { situacao: Situacao; nomeAtual?: string; aoUsarNome?: (nome: string) => void }) {
  const podeTrocarNome = aoUsarNome && situacao.nomeOficial && situacao.nomeOficial !== nomeAtual?.trim();
  return (
    <Alert
      type={situacao.alerta}
      showIcon
      title={situacao.mensagem}
      action={podeTrocarNome ? <Button size="small" onClick={() => aoUsarNome(situacao.nomeOficial)}>Usar nome oficial</Button> : undefined}
      style={{ marginBottom: "var(--ant-margin)" }}
    />
  );
}

const ICONE_DO_SUBTIPO: Record<string, ReactNode> = {
  hospital: <MedicineBoxOutlined />,
  clinica: <ShopOutlined />,
  laboratorio: <ExperimentOutlined />,
  profissional: <UserOutlined />,
  operadora: <SafetyCertificateOutlined />,
  autogestao: <TeamOutlined />,
  healthtech_consultoria: <CodeOutlined />,
  sus_governo: <GlobalOutlined />,
  outro: <AppstoreOutlined />,
};

const GRUPOS = [
  { rotulo: "Prestador", tipos: ["prov"] },
  { rotulo: "Operadora", tipos: ["pay"] },
  { rotulo: "Outros", tipos: ["bus", "govt", "other"] },
];

function PapelDaOrg({
  subtipos,
  value,
  onChange,
}: {
  subtipos: Subtipo[];
  value?: string;
  onChange?: (valor: string) => void;
}) {
  const { token } = theme.useToken();
  const conhecidos = new Set(GRUPOS.flatMap((grupo) => grupo.tipos));
  const grupos = [
    ...GRUPOS.map((grupo) => ({ ...grupo, itens: subtipos.filter((item) => grupo.tipos.includes(item.type)) })),
    { rotulo: "Outros tipos", tipos: [], itens: subtipos.filter((item) => !conhecidos.has(item.type)) },
  ].filter((grupo) => grupo.itens.length > 0);

  return (
    <Flex vertical gap={token.margin} role="radiogroup" aria-label="Tipo">
      {grupos.map((grupo) => (
        <Flex key={grupo.rotulo} vertical gap={token.marginXS}>
          <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
            {grupo.rotulo}
          </Typography.Text>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: token.marginXS }}>
            {grupo.itens.map((item) => {
              const marcado = value === item.code;
              return (
                <button
                  key={item.code}
                  type="button"
                  role="radio"
                  aria-checked={marcado}
                  onClick={() => onChange?.(item.code)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: token.marginXS,
                    minWidth: 0,
                    minHeight: 48,
                    padding: `${token.paddingXS}px ${token.paddingSM}px`,
                    border: `1px solid ${marcado ? token.colorPrimary : token.colorBorder}`,
                    borderRadius: token.borderRadiusLG,
                    background: marcado ? token.colorPrimaryBg : token.colorBgContainer,
                    boxShadow: marcado ? `0 0 0 1px ${token.colorPrimary}` : "none",
                    color: marcado ? token.colorPrimaryText : token.colorText,
                    cursor: "pointer",
                    font: "inherit",
                    textAlign: "left",
                    transition: `border-color ${token.motionDurationMid}, background ${token.motionDurationMid}`,
                  }}
                >
                  <span style={{ fontSize: token.fontSizeLG, color: marcado ? token.colorPrimary : token.colorTextSecondary }}>
                    {ICONE_DO_SUBTIPO[item.code] ?? <AppstoreOutlined />}
                  </span>
                  <span style={{ minWidth: 0, lineHeight: token.lineHeightSM }}>{item.display.replaceAll("/", "/\u200b")}</span>
                </button>
              );
            })}
          </div>
        </Flex>
      ))}
    </Flex>
  );
}

export function Onboarding({
  catalogo,
  podeVoltar,
  orgInicial,
}: {
  catalogo: CatalogoDeOrgs;
  podeVoltar: boolean;
  orgInicial?: string;
}) {
  const { token } = theme.useToken();
  const [form] = Form.useForm<Campos>();
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [emUso, setEmUso] = useState<{ chave: string; mensagem: string } | null>(null);
  const [busca, setBusca] = useState<{ chave: string; situacao: Situacao } | null>(null);
  const ultimaBusca = useRef("");
  const prontas = catalogo.organizations.filter((org) => org.tiss_org && org.terms.accepted);
  const aceitaveis = catalogo.organizations.filter((org) => org.is_admin && !(org.tiss_org && org.terms.accepted));
  const inicial = aceitaveis.find((org) => org.id === orgInicial);
  const destino = Form.useWatch("destino", form) ?? NOVA;
  const subtipo = Form.useWatch("subtype", form);
  const tipo = catalogo.subtypes.find((item) => item.code === subtipo)?.type;
  const chaveAtual = textoDaChave(chaveDaBusca(tipo, Form.useWatch("cnpj", form), Form.useWatch("registro_ans", form)));
  const situacao = busca && busca.chave === chaveAtual ? busca.situacao : null;

  async function buscar() {
    const tipoAtual = catalogo.subtypes.find((item) => item.code === form.getFieldValue("subtype"))?.type;
    const chave = chaveDaBusca(tipoAtual, form.getFieldValue("cnpj"), form.getFieldValue("registro_ans"));
    const texto = textoDaChave(chave);
    if (!chave || texto === ultimaBusca.current) return;
    ultimaBusca.current = texto;
    let resposta;
    try {
      resposta = lerResposta(await pedir(caminhoDaBusca(chave)));
    } catch (motivo) {
      if (motivo instanceof FalhaDoPedido && motivo.status === 400) return;
      resposta = lerResposta(null);
    }
    if (ultimaBusca.current !== texto) return;
    setBusca({ chave: texto, situacao: situacaoDaBusca(resposta, chave.campo) });
    if ((form.getFieldValue("destino") ?? NOVA) === NOVA) {
      const nome = nomeSugerido(form.getFieldValue("name"), resposta);
      if (nome) form.setFieldValue("name", nome);
    }
  }

  function preencher(id: string) {
    const org = aceitaveis.find((item) => item.id === id);
    if (!org) return;
    form.setFieldsValue({
      cnpj: org.cnpj || undefined,
      registro_ans: org.registro_ans || undefined,
      subtype: org.subtype || undefined,
    });
    void buscar();
  }

  async function enviar(valores: Campos) {
    const nova = (valores.destino ?? NOVA) === NOVA;
    setEnviando(true);
    setErro("");
    setEmUso(null);
    try {
      const identidade = {
        subtype: valores.subtype,
        cnpj: valores.cnpj,
        ...(tipo === "pay" ? { registro_ans: valores.registro_ans } : {}),
        ...(tipo !== "pay" && valores.cnes?.trim() ? { cnes: valores.cnes.trim() } : {}),
        accept_terms_version: catalogo.terms_version,
      };
      const org = nova
        ? await pedir<EstadoDaOrg>("me/tiss/organizations/", { method: "POST", body: { name: valores.name, ...identidade } })
        : await pedir<EstadoDaOrg>(`org/${valores.destino}/tiss/onboard/`, { method: "POST", body: identidade });
      abrirDeNovo(hrefDaOrg(org.id, "visao"));
    } catch (motivo) {
      if (motivo instanceof FalhaDoPedido) {
        const nomes = new Set(["name", "subtype", "cnpj", "registro_ans", "cnes"]);
        const campos = Object.entries(motivo.campos).filter(([campo]) => nomes.has(campo));
        form.setFields(campos.map(([name, mensagem]) => ({ name: name as keyof Campos, errors: [mensagem] })));
        const ocupado = [...campos.map(([, mensagem]) => mensagem), motivo.message].find((mensagem) => EM_USO.test(mensagem));
        if (ocupado) setEmUso({ chave: chaveAtual, mensagem: ocupado });
        else if (campos.length === 0) setErro(motivo.message);
      } else {
        setErro("Não foi possível criar a organização.");
      }
      setEnviando(false);
    }
  }

  return (
    <Flex vertical align="center" style={{ minHeight: "100vh", padding: token.paddingLG, background: token.colorBgLayout }}>
      <Flex vertical gap={token.marginLG} style={{ width: "100%", maxWidth: 720 }}>
        <Flex align="center" justify="space-between" gap={token.margin}>
          <Link href="/" aria-label="tiss, página inicial" style={{ display: "inline-flex" }}>
            <Image src="/logo.svg" alt="Voa" width={88} height={24} priority />
          </Link>
          <Flex gap={token.marginSM}>
            {podeVoltar && <Button href="/org">Voltar ao painel</Button>}
            <Button onClick={() => void sair()}>Sair</Button>
          </Flex>
        </Flex>
        <Typography.Title level={1} style={{ margin: 0, fontSize: token.fontSizeHeading2 }}>
          Cadastre sua organização
        </Typography.Title>
        {prontas.length > 0 && (
          <Card title="Suas organizações">
            <Flex vertical gap={token.marginSM}>
              {prontas.map((org) => (
                <Flex key={org.id} wrap align="center" justify="space-between" gap={token.marginSM}>
                  <Typography.Text>
                    {org.name} · {ROTULO_DO_TIPO[org.type] ?? org.type_display}
                  </Typography.Text>
                  <Button href={hrefDaOrg(org.id, "visao")}>Abrir</Button>
                </Flex>
              ))}
            </Flex>
          </Card>
        )}
        <Card>
          {erro && <Alert type="error" showIcon title={erro} style={{ marginBottom: token.margin }} />}
          {emUso && emUso.chave === chaveAtual && (
            <Alert
              type="warning"
              showIcon
              title={emUso.mensagem}
              description="Peça a quem administra que convide você em Membros."
              style={{ marginBottom: token.margin }}
            />
          )}
          <Form<Campos>
            form={form}
            layout="vertical"
            initialValues={{
              destino: inicial?.id ?? NOVA,
              aceite: false,
              cnpj: inicial?.cnpj || undefined,
              registro_ans: inicial?.registro_ans || undefined,
              subtype: inicial?.subtype || undefined,
            }}
            onFinish={(valores) => void enviar(valores)}
          >
            {aceitaveis.length > 0 && (
              <Form.Item name="destino" label="Organização">
                <Select
                  onChange={preencher}
                  options={[
                    { value: NOVA, label: "Nova organização" },
                    ...aceitaveis.map((org) => ({ value: org.id, label: `${org.name} (já existe na Voa)` })),
                  ]}
                />
              </Form.Item>
            )}
            <Form.Item name="subtype" label="Tipo" rules={[{ required: true, message: "Escolha o tipo." }]}>
              <PapelDaOrg subtipos={catalogo.subtypes} />
            </Form.Item>
            <Row gutter={token.margin}>
              {tipo !== "pay" && (
                <Col xs={24} sm={10}>
                  <Form.Item name="cnes" label="CNES (opcional)">
                    <AutoComplete
                      popupMatchSelectWidth={false}
                      options={situacao?.unidades.map((unidade) => ({ value: unidade.cnes, label: rotuloDaUnidade(unidade) }))}
                    >
                      <Input allowClear inputMode="numeric" placeholder="0000000" />
                    </AutoComplete>
                  </Form.Item>
                </Col>
              )}
              <Col xs={24} sm={14}>
                <Form.Item name="cnpj" label="CNPJ" rules={[{ required: true, whitespace: true, message: "Informe o CNPJ." }]}>
                  <Input inputMode="numeric" placeholder="00.000.000/0000-00" onBlur={() => void buscar()} />
                </Form.Item>
              </Col>
              {tipo === "pay" && (
                <Col xs={24} sm={10}>
                  <Form.Item
                    name="registro_ans"
                    label="Registro ANS"
                    rules={[{ required: true, whitespace: true, message: "Informe o registro ANS." }]}
                  >
                    <Input inputMode="numeric" placeholder="000000" onBlur={() => void buscar()} />
                  </Form.Item>
                </Col>
              )}
            </Row>
            {situacao?.mensagem && (
              <AvisoDaBusca
                situacao={situacao}
                nomeAtual={form.getFieldValue("name")}
                aoUsarNome={destino === NOVA ? (nome) => form.setFieldValue("name", nome) : undefined}
              />
            )}
            {destino === NOVA && (
              <Form.Item name="name" label="Nome" rules={[{ required: true, whitespace: true, message: "Informe o nome." }]}>
                <Input autoComplete="organization" />
              </Form.Item>
            )}
            <Form.Item
              name="aceite"
              valuePropName="checked"
              rules={[
                {
                  validator: (_, valor) => (valor ? Promise.resolve() : Promise.reject(new Error("Aceite os termos para continuar."))),
                },
              ]}
            >
              <Checkbox>
                Li e aceito os <a href={catalogo.terms_url || "/termos"} target="_blank" rel="noreferrer">termos de uso</a>{" "}
                (versão {catalogo.terms_version})
              </Checkbox>
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={enviando}>Cadastrar</Button>
          </Form>
        </Card>
      </Flex>
    </Flex>
  );
}
