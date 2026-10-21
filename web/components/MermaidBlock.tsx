"use client";

import { Alert, theme } from "antd";
import { useEffect, useState } from "react";

export function MermaidBlock({ chart }: { chart: string }) {
  const { token } = theme.useToken();
  const [svg, setSvg] = useState("");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    import("mermaid")
      .then(async ({ default: mermaid }) => {
        mermaid.initialize({
          startOnLoad: false,
          theme: "base",
          themeVariables: {
            fontFamily: token.fontFamily,
            primaryColor: token.colorPrimaryBg,
            primaryBorderColor: token.colorPrimaryBorder,
            primaryTextColor: token.colorText,
            lineColor: token.colorPrimaryBorder,
            secondaryColor: token.colorPrimaryBg,
            tertiaryColor: token.colorBgContainer,
          },
        });
        const result = await mermaid.render(`diagram-${crypto.randomUUID()}`, chart);
        if (active) setSvg(result.svg);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, [chart, token]);

  if (failed) return <Alert type="error" title="Não foi possível exibir o diagrama." />;
  if (!svg) {
    return (
      <div aria-label="Carregando diagrama" style={{ color: token.colorTextSecondary }}>
        Carregando diagrama…
      </div>
    );
  }
  return (
    <div
      role="img"
      aria-label="Diagrama"
      style={{ maxWidth: "100%", overflowX: "auto" }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
