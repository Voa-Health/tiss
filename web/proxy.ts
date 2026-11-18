const ORG_PANEL_PATH = "/org";
const EMAIL_VERIFICATION_PATH = "/org/verificar";
const CONSOLE_URL = "https://console.voa.health";

type ProxyRequest = { method: string; nextUrl: URL };

export function proxy(request: ProxyRequest): Response | undefined {
  const pathname = request.nextUrl.pathname;
  if (
    request.method !== "GET" ||
    pathname === EMAIL_VERIFICATION_PATH ||
    pathname === `${EMAIL_VERIFICATION_PATH}/` ||
    (pathname !== ORG_PANEL_PATH && !pathname.startsWith(`${ORG_PANEL_PATH}/`))
  ) {
    return;
  }
  return Response.redirect(CONSOLE_URL, 308);
}

export const config = {
  matcher: ["/org/:path*"],
};
