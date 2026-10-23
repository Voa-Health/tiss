import OrgPage from "@/components/org/OrgPage";

export { metadata } from "@/components/org/OrgPage";
export const dynamic = "force-dynamic";

export default function CobrancaPage(props: Parameters<typeof OrgPage>[0]) {
  return <OrgPage {...props} secao="cobranca" />;
}
