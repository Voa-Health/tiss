"use client";

import Link from "next/link";
import { Button, Result } from "antd";
import { site } from "@/lib/site";

export default function NotFound() {
  return (
    <Result
      status="404"
      title="Página não encontrada"
      subTitle="Confira o endereço ou volte à página inicial."
      extra={<Button type="primary" href="/">Página inicial</Button>}
    >
      <Link href={site.docsUrl}>Acessar a documentação</Link>
    </Result>
  );
}
