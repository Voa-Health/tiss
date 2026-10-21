"use client";

import Link from "next/link";
import { Button, Result } from "antd";

export default function NotFound() {
  return (
    <Result
      status="404"
      title="Página não encontrada"
      subTitle="Confira o endereço ou volte à página inicial."
      extra={<Button type="primary" href="/">Página inicial</Button>}
    >
      <Link href="/docs">Acessar a documentação</Link>
    </Result>
  );
}
