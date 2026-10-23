"use client";

import Link from "next/link";
import { Button, Result } from "antd";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { ContentWrapper } from "@/components/ui/ContentWrapper";
import { site } from "@/lib/site";

export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <ContentWrapper>
        <Result
          status="404"
          title="Página não encontrada"
          subTitle="Confira o endereço ou volte à página inicial."
          extra={<Button type="primary" href="/">Página inicial</Button>}
        >
          <Link href={site.docsUrl}>Acessar a documentação</Link>
        </Result>
      </ContentWrapper>
      <SiteFooter />
    </>
  );
}
