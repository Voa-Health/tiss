import OrgPage from "@/components/org/OrgPage";

export { metadata } from "@/components/org/OrgPage";
export const dynamic = "force-dynamic";

type Props = { params: Promise<{ orgId: string }>; searchParams: Parameters<typeof OrgPage>[0]["searchParams"] };

export default async function PaginaDaOrg({ params, searchParams }: Props) {
  return <OrgPage orgId={(await params).orgId} searchParams={searchParams} />;
}
