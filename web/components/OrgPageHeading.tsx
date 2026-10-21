"use client";

import { Flex, Tag, Typography } from "antd";
import { PageHeader } from "@/components/ui/PageHeader";

export function OrgPageHeading({ name }: { name: string }) {
  return (
    <PageHeader>
      <Flex
        align="center"
        style={{ flexWrap: "wrap", gap: "var(--ant-margin)", minWidth: 0 }}
      >
        <Typography.Title level={1} style={{ margin: 0 }}>
          {name}
        </Typography.Title>
        <Tag color="processing">Protótipo</Tag>
      </Flex>
    </PageHeader>
  );
}
