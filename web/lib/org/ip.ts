const IP = /^[0-9A-Fa-f:.]{2,45}$/;

/** IP do navegador; a Vercel reescreve `x-forwarded-for` na entrada do site. */
export function ipDoCliente(cabecalhos: Headers): string | null {
  const encaminhado = cabecalhos.get("x-forwarded-for")?.split(",")[0]?.trim();
  const ip = encaminhado || cabecalhos.get("x-real-ip")?.trim() || "";
  return IP.test(ip) ? ip : null;
}

/** Para o backend limitar cadastros por navegador, não pelo servidor. */
export function cabecalhosDoCliente(cabecalhos: Headers): Record<string, string> {
  const ip = ipDoCliente(cabecalhos);
  return ip ? { "x-forwarded-for": ip, "x-real-ip": ip } : {};
}
