"use client";

import { Button, Col, Flex, Row, Typography, theme } from "antd";
import Link from "next/link";
import { CodeBlock } from "@/components/CodeBlock";
import { Section } from "@/components/ui/Section";
import { track } from "@/lib/analytics";
import { site } from "@/lib/site";

const sample = `{
  "operadora": "Operadora Exemplo",
  "mantenedor": { "tipo": "operadora", "registro_ans": "123456" },
  "official": true,
  "versao_tiss": "4.03.00",
  "regras": [
    {
      "id": "exemplo.campo-obrigatorio",
      "descricao": "Informe o número da guia do prestador.",
      "source": {
        "url": "https://example.org/manual",
        "titulo": "Manual público de exemplo",
        "data": "2026-01-15",
        "acesso": "https://example.org/manual"
      },
      "severity": "error",
      "check": { "tipo": "obrigatorio", "pointer": "/guias/*/numeroGuiaPrestador" }
    }
  ]
}`;

export function HealthplanPublishing() {
  const { token } = theme.useToken();
  return (
    <Section
      id="publicar-regras"
      title="Publique suas regras com selo Oficial"
      description="Prestadores validam as guias com as regras da operadora antes do envio, reduzindo glosas por erro de preenchimento."
    >
      <Row gutter={[token.marginLG, token.marginLG]}>
        <Col xs={24} lg={12}>
          <Flex vertical gap={token.margin} align="flex-start">
            <ol style={{ margin: 0, paddingInlineStart: token.paddingLG }}>
              <li>
                Crie um pacote JSON no formato{" "}
                <Link href={`${site.github}/blob/main/schemas/rules.schema.json`}>
                  schemas/rules.schema.json
                </Link>{" "}
                e salve em{" "}
                <code>src/tiss/rules/NNNNNN.json</code>, com o registro ANS de seis dígitos no
                nome.
              </li>
              <li>
                Inclua a fonte publicada e a data em cada regra, além de{" "}
                <code>{'mantenedor: {"tipo": "operadora", "registro_ans": "…"}'}</code>.
              </li>
              <li>
                Envie sua contribuição pelo GitHub; as verificações automáticas validam o pacote.
              </li>
              <li>
                Após aprovação por responsável com e-mail no domínio cadastrado da operadora na ANS,
                o pacote recebe o selo Oficial.
              </li>
              <li>Envie novas contribuições pelo GitHub para manter e atualizar as regras.</li>
            </ol>
            <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
              O selo Oficial aparece em <code>validate</code>, nas páginas de operadora e no MCP.
            </Typography.Paragraph>
            <Button
              type="primary"
              href={site.healthplanContactUrl}
              onClick={() => track("tiss_operadora_contact", { local: "operadoras" })}
            >
              Falar com a equipe
            </Button>
          </Flex>
        </Col>
        <Col xs={24} lg={12}>
          <CodeBlock code={sample} />
        </Col>
      </Row>
    </Section>
  );
}
