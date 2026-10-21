import { ImageResponse } from "next/og";
import { light } from "@/tema/light";

export const alt = "voa-tiss — validação de lotes TISS";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  const color = String(light.token?.colorPrimary);
  const background = String(light.token?.colorBgBase);
  const foreground = String(light.token?.colorText);
  const pad = light.token?.paddingXL ?? 0;
  const sectionGap = light.token?.marginLG ?? 0;
  const largeFont = light.token?.fontSizeHeading1 ?? 0;
  const mediumFont = light.token?.fontSizeHeading2 ?? 0;
  return new ImageResponse(
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        width: "100%",
        height: "100%",
        padding: pad,
        backgroundColor: background,
        color: foreground,
        borderTop: `${sectionGap}px solid ${color}`,
        fontFamily: "sans-serif",
      }}
    >
      <div style={{ color, fontSize: mediumFont }}>voa-tiss</div>
      <div style={{ fontSize: largeFont, fontWeight: 600, marginTop: sectionGap }}>
        Valide lotes TISS
      </div>
      <div style={{ fontSize: mediumFont, marginTop: light.token?.margin ?? 0 }}>
        Valide, corrija e revalide antes do envio.
      </div>
    </div>,
    size,
  );
}
