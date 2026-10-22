"use client";

import { CopyOutlined } from "@ant-design/icons";
import { Button, Card, Col, Flex, InputNumber, Row, Statistic, Typography, theme } from "antd";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { track } from "@/lib/analytics";
import { OpenLibraryCard } from "@/components/OpenLibraryCard";
import { calculatorBands } from "@/lib/calculator";
import { launchPrices } from "@/lib/modules";

const defaults = {
  faturamento: 1_000_000,
  percentual: 5,
  glosa: 10,
  recorridas: 50,
  valor_medio: 300,
};

function readValue(raw: string | null, fallback: number): number {
  const value = raw === null ? fallback : Number(raw);
  return Number.isFinite(value) && value >= 0 ? value : fallback;
}

function currency(value: number): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
}

function numberInput(
  label: string,
  value: number,
  onChange: (value: number) => void,
  money = false,
) {
  return (
    <InputNumber
      aria-label={label}
      min={0}
      value={value}
      onChange={(next) => onChange(next ?? 0)}
      formatter={(next) =>
        next === undefined || next === null
          ? ""
          : `${money ? "R$ " : ""}${new Intl.NumberFormat("pt-BR").format(Number(next))}`
      }
      parser={(raw) =>
        Number(raw?.replace(/[^\d,-]/g, "").replace(/\./g, "").replace(",", ".") ?? 0)
      }
      style={{ width: "100%" }}
    />
  );
}

export function Calculator() {
  const { token } = theme.useToken();
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [faturamento, setFaturamento] = useState(() => readValue(searchParams.get("faturamento"), defaults.faturamento));
  const [percentual, setPercentual] = useState(() => readValue(searchParams.get("percentual"), defaults.percentual));
  const [glosa, setGlosa] = useState(() => readValue(searchParams.get("glosa"), defaults.glosa));
  const [recorridas, setRecorridas] = useState(() => readValue(searchParams.get("recorridas"), defaults.recorridas));
  const [valorMedio, setValorMedio] = useState(() => readValue(searchParams.get("valor_medio"), defaults.valor_medio));
  const [preco, setPreco] = useState(() =>
    readValue(searchParams.get("preco"), launchPrices.recurso.amount ?? 0),
  );
  const [copied, setCopied] = useState(false);
  const lastBands = useRef<string | null>(null);
  const initialParams = searchParams.toString();
  const price = launchPrices.recurso.amount;
  const resources = valorMedio > 0
    ? Math.ceil((faturamento * (glosa / 100) * (recorridas / 100)) / valorMedio)
    : 0;
  const moduleCost = resources * (price ?? preco);
  const currentCost = faturamento * (percentual / 100);
  const difference = currentCost - moduleCost;
  const differenceLabel = difference >= 0 ? "Economia mensal estimada" : "Custo adicional estimado";

  useEffect(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("faturamento", String(faturamento));
    params.set("percentual", String(percentual));
    params.set("glosa", String(glosa));
    params.set("recorridas", String(recorridas));
    params.set("valor_medio", String(valorMedio));
    if (price === null) params.set("preco", String(preco));
    else params.delete("preco");
    const query = params.toString();
    if (query !== initialParams) router.replace(`${pathname}?${query}`, { scroll: false });
  }, [
    faturamento,
    percentual,
    glosa,
    recorridas,
    valorMedio,
    preco,
    price,
    initialParams,
    pathname,
    router,
    searchParams,
  ]);

  useEffect(() => {
    const values = { faturamento, percentual, glosa, recorridas, valor_medio: valorMedio };
    const bands = calculatorBands(values);
    const signature = JSON.stringify(bands);
    if (lastBands.current === null) {
      lastBands.current = signature;
      return;
    }
    if (lastBands.current === signature) return;
    const timeout = setTimeout(() => {
      lastBands.current = signature;
      track("tiss_calculator_use", bands);
    }, 2_000);
    return () => clearTimeout(timeout);
  }, [faturamento, percentual, glosa, recorridas, valorMedio]);

  async function copyLink() {
    await navigator.clipboard.writeText(window.location.href);
    setCopied(true);
  }

  const fields = [
    {
      key: "faturamento",
      label: "Faturamento mensal",
      value: faturamento,
      setValue: setFaturamento,
      money: true,
    },
    {
      key: "percentual",
      label: "% cobrado hoje pelo BPO",
      value: percentual,
      setValue: setPercentual,
    },
    { key: "glosa", label: "Taxa de glosa (%)", value: glosa, setValue: setGlosa },
    {
      key: "recorridas",
      label: "% das glosas recorridas",
      value: recorridas,
      setValue: setRecorridas,
    },
    {
      key: "valor_medio",
      label: "Valor médio de um item glosado",
      value: valorMedio,
      setValue: setValorMedio,
      money: true,
    },
  ];

  return (
    <Flex vertical gap={token.paddingLG}>
      <section>
        <Typography.Title>Calculadora de economia mensal</Typography.Title>
        <Typography.Paragraph>
          Estime o custo dos recursos de glosa a partir do faturamento, taxa de glosa e volume recorrido.
        </Typography.Paragraph>
      </section>
      <Row gutter={[token.margin, token.margin]}>
        {fields.map((field) => (
          <Col key={field.key} xs={24} sm={12} md={8}>
            <Flex vertical gap={token.marginXS}>
              <Typography.Text>{field.label}</Typography.Text>
              {numberInput(field.label, field.value, field.setValue, field.money)}
            </Flex>
          </Col>
        ))}
        {price === null && (
          <Col xs={24} sm={12} md={8}>
            <Flex vertical gap={token.marginXS}>
              <Typography.Text>Preço por recurso (R$)</Typography.Text>
              {numberInput("Preço por recurso (R$)", preco, setPreco, true)}
            </Flex>
          </Col>
        )}
      </Row>
      <Row gutter={[token.margin, token.margin]}>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="Custo atual" value={currentCost} formatter={() => currency(currentCost)} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="Recursos por mês" value={resources} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="Custo com o módulo" value={moduleCost} formatter={() => currency(moduleCost)} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title={differenceLabel}
              value={Math.abs(difference)}
              formatter={() => currency(Math.abs(difference))}
              valueStyle={{ color: difference >= 0 ? token.colorSuccess : token.colorError }}
            />
          </Card>
        </Col>
      </Row>
      <Card>
        <Typography.Paragraph>
          A estimativa calcula recursos = teto(faturamento × glosa ÷ 100 × glosas recorridas ÷ 100 ÷
          valor médio do item) e custo do módulo = recursos × preço por recurso.
        </Typography.Paragraph>
        <Typography.Paragraph>
          O percentual do BPO remunera toda a operação de faturamento; o módulo cobre apenas o recurso de
          glosa. Os valores não são uma substituição equivalente. É uma estimativa, não uma proposta comercial.
          O cálculo acontece no navegador e nada é enviado.
        </Typography.Paragraph>
        <Button icon={<CopyOutlined />} onClick={() => void copyLink()}>
          {copied ? "Link copiado" : "Copiar link"}
        </Button>
      </Card>
      <OpenLibraryCard />
    </Flex>
  );
}
