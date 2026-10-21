"use client";

import { Card, Collapse, Flex, Row, Col, Statistic, Table, theme, Typography } from "antd";
import type { TableColumnsType } from "antd";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/site";
import type { UsageDay } from "@/lib/org-mock";

type Totals = { validate: number; sandbox: number; mcp: number; all: number };

function usageTotals(days: UsageDay[]): Totals {
  return days.reduce(
    (total, day) => ({
      validate: total.validate + day.validate,
      sandbox: total.sandbox + day.sandbox,
      mcp: total.mcp + day.mcp,
      all: total.all + day.validate + day.sandbox + day.mcp,
    }),
    { validate: 0, sandbox: 0, mcp: 0, all: 0 },
  );
}

function UsageChart({ days, totals }: { days: UsageDay[]; totals: Totals }) {
  const { token } = theme.useToken();
  const colors = [
    token.colorPrimary,
    token.colorSuccessTextActive,
    token.colorText,
  ];
  const maxTotal = Math.max(1, ...days.map((day) => day.validate + day.sandbox + day.mcp));
  const baseline = 190;
  const plotHeight = 160;
  const summary =
    `Uso nos últimos ${days.length} dias: ${totals.all} chamadas; ` +
    `${totals.validate} validações, ${totals.sandbox} simulações e ${totals.mcp} operações MCP.`;

  return (
    <Card title="Uso por dia">
      <Flex vertical gap={token.margin}>
        <svg
          viewBox="0 0 900 220"
          role="img"
          aria-label={summary}
          style={{ display: "block", width: "100%", height: "auto" }}
        >
          <line
            x1="8"
            y1={baseline}
            x2="892"
            y2={baseline}
            stroke={token.colorBorderSecondary}
            strokeWidth={token.lineWidth}
          />
          {days.map((day, index) => {
            const x = 16 + index * 29;
            let y = baseline;
            const values = [
              { value: day.validate, color: colors[0] },
              { value: day.sandbox, color: colors[1] },
              { value: day.mcp, color: colors[2] },
            ];
            return (
              <g key={day.dia}>
                {values.map(({ value, color }, part) => {
                  const height = (value / maxTotal) * plotHeight;
                  y -= height;
                  return (
                    <rect
                      key={part}
                      x={x}
                      y={y}
                      width="17"
                      height={height}
                      fill={color}
                    />
                  );
                })}
              </g>
            );
          })}
        </svg>
        <Flex wrap gap={token.margin}>
          {[
            { label: "Validação", color: colors[0] },
            { label: "Operadora simulada", color: colors[1] },
            { label: "MCP", color: colors[2] },
          ].map(({ label, color }) => (
            <Flex key={label} align="center" gap={token.marginXS}>
              <span
                aria-hidden="true"
                style={{
                  width: token.sizeXS,
                  height: token.sizeXS,
                  borderRadius: token.borderRadiusXS,
                  background: color,
                }}
              />
              <Typography.Text>{label}</Typography.Text>
            </Flex>
          ))}
        </Flex>
      </Flex>
    </Card>
  );
}

export function UsageSection({ days }: { days: UsageDay[] }) {
  const { token } = theme.useToken();
  if (!days.length) {
    return (
      <EmptyState
        title="Sem uso registrado"
        description={
          <Typography.Text style={{ color: token.colorTextSecondary }}>
            Os dados de uso da organização aparecerão aqui.
          </Typography.Text>
        }
      />
    );
  }

  const totals = usageTotals(days);
  const columns: TableColumnsType<UsageDay> = [
    { title: "Dia", dataIndex: "dia", key: "dia", render: (value: string) => formatDate(value) },
    { title: "Validação", dataIndex: "validate", key: "validate" },
    { title: "Operadora simulada", dataIndex: "sandbox", key: "sandbox" },
    { title: "MCP", dataIndex: "mcp", key: "mcp" },
  ];
  const statistics = [
    { title: "Total (30 dias)", value: totals.all },
    { title: "Validação", value: totals.validate },
    { title: "Operadora simulada", value: totals.sandbox },
    { title: "MCP", value: totals.mcp },
  ];

  return (
    <Flex vertical gap={token.marginLG}>
      <Row gutter={[token.margin, token.margin]}>
        {statistics.map((stat) => (
          <Col key={stat.title} xs={24} sm={12} xl={6}>
            <Card style={{ height: "100%" }}>
              <Statistic
                title={
                  <Typography.Text style={{ color: token.colorTextSecondary }}>
                    {stat.title}
                  </Typography.Text>
                }
                value={stat.value}
              />
            </Card>
          </Col>
        ))}
      </Row>
      <UsageChart days={days} totals={totals} />
      <Collapse
        items={[
          {
            key: "dados",
            label: "Ver dados por dia",
            children: (
              <div aria-label="Detalhamento diário do uso" role="region">
                <Table
                  rowKey="dia"
                  columns={columns}
                  dataSource={days}
                  pagination={false}
                  scroll={{ x: 560 }}
                />
              </div>
            ),
          },
        ]}
      />
    </Flex>
  );
}
