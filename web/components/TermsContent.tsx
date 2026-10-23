"use client";

import { Typography } from "antd";

export function TermsContent() {
  return (
    <>
      <Typography.Title>Termos</Typography.Title>
      <Typography.Paragraph>Versão 2026-10</Typography.Paragraph>
      <Typography.Title level={2} id="mapa-de-rejeicao">
        Mapa de rejeição
      </Typography.Title>
      <Typography.Paragraph>
        A coleta do mapa hospedado é opcional e desligada por padrão. Ao ativá-la
        no /org, a organização autoriza o envio de agregados por prestador,
        código, regra e mês. O CPF é pseudonimizado com HMAC e segredo próprio da
        organização antes de sair do cliente; o CNPJ permanece em claro. O código
        do prestador na operadora tem preferência quando informado.
      </Typography.Paragraph>
      <Typography.Paragraph>
        A retenção é de 24 meses. A organização pode desligar a coleta e apagar
        todos os dados do mapa no /org. Esse aceite não altera a telemetria
        anônima, que permanece independente.
      </Typography.Paragraph>
    </>
  );
}
