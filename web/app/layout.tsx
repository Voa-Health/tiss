import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import type { ReactNode } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ContentWrapper } from "@/components/ui/ContentWrapper";
import { robotsPolicy, site } from "@/lib/site";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-plex-sans",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  metadataBase: new URL(site.url),
  title: { default: "voa-tiss", template: "%s · voa-tiss" },
  description: "Valide lotes TISS, corrija achados e revalide antes do envio à operadora.",
  robots: robotsPolicy(),
  openGraph: {
    type: "website",
    locale: "pt_BR",
    siteName: site.name,
    title: "voa-tiss",
    description: "Valide, corrija e revalide lotes TISS.",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR" className={`${plexSans.variable} ${plexMono.variable}`}>
      <body>
        <ThemeProvider>
          <SiteHeader />
          <ContentWrapper>{children}</ContentWrapper>
          <SiteFooter />
        </ThemeProvider>
      </body>
    </html>
  );
}
