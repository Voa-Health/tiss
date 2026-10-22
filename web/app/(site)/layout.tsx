import type { ReactNode } from "react";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { ContentWrapper } from "@/components/ui/ContentWrapper";

export default function SiteLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <SiteHeader />
      <ContentWrapper>{children}</ContentWrapper>
      <SiteFooter />
    </>
  );
}
