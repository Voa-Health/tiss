"use client";

import { ArrowRightOutlined } from "@ant-design/icons";
import { Card, Col, Flex, Row, Segmented, Typography, theme } from "antd";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import type { AudienceItem } from "@/lib/audiences";

export function TerminalGif({
  item,
  priority = false,
}: {
  item: AudienceItem;
  priority?: boolean;
}) {
  const { token } = theme.useToken();
  if (!item.demo) return null;
  return (
    <Image
      key={item.demo.src}
      src={item.demo.src}
      alt={item.demo.alt}
      width={item.demo.width}
      height={item.demo.height}
      priority={priority}
      unoptimized
      style={{
        display: "block",
        width: "100%",
        height: "auto",
        aspectRatio: `${item.demo.width} / ${item.demo.height}`,
        borderRadius: token.borderRadiusLG,
        background: "#1c1b29",
      }}
    />
  );
}

export function FeatureDemos({ items }: { items: AudienceItem[] }) {
  const { token } = theme.useToken();
  const [active, setActive] = useState(items[0].label);
  const item =
    items.find((candidate) => candidate.label === active) ?? items[0];
  return (
    <Card>
      <Flex vertical gap={token.marginLG}>
        <div style={{ overflowX: "auto" }}>
          <Segmented
            value={active}
            onChange={(value) => setActive(String(value))}
            options={items.map((candidate) => candidate.label)}
          />
        </div>
        <Row gutter={[token.marginLG, token.marginLG]} align="middle">
          <Col xs={24} lg={14}>
            <TerminalGif item={item} />
          </Col>
          <Col xs={24} lg={10}>
            <Flex vertical gap={token.marginSM} align="flex-start">
              <Typography.Title
                level={3}
                style={{ margin: 0, fontSize: token.fontSizeHeading4 }}
              >
                {item.label}
              </Typography.Title>
              <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
                {item.description}
              </Typography.Paragraph>
              <Link href={item.href}>
                {item.linkLabel} <ArrowRightOutlined aria-hidden="true" />
              </Link>
            </Flex>
          </Col>
        </Row>
      </Flex>
    </Card>
  );
}
