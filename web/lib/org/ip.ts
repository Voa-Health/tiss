import { isIP } from "node:net";

/** IP do navegador; a Vercel reescreve `x-forwarded-for` na entrada do site. */
export function ipDoCliente(cabecalhos: Headers): string | null {
  const encaminhado = cabecalhos.get("x-forwarded-for")?.split(",")[0]?.trim();
  const ip = encaminhado || cabecalhos.get("x-real-ip")?.trim() || "";
  return isIP(ip) ? ip : null;
}

/** A Vercel do backend também reescreve `x-forwarded-for`; o segredo prova que o IP veio do site. */
export function cabecalhosDoCliente(cabecalhos: Headers): Record<string, string> {
  const ip = ipDoCliente(cabecalhos);
  const segredo = process.env.TISS_SERVICE_SECRET?.trim();
  return ip && segredo ? { "x-voa-client-ip": ip, "x-voa-service-secret": segredo } : {};
}
