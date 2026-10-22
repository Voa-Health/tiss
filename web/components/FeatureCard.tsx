"use client";

import { ArrowRightOutlined } from "@ant-design/icons";
import { Card, Col, Flex, Row, Typography, theme } from "antd";
import Image from "next/image";
import Link from "next/link";
import type { AudienceItem } from "@/lib/audiences";

function FeatureText({ item }: { item: AudienceItem }) {
  const { token } = theme.useToken();
  return (
    <Flex vertical gap={token.marginSM}>
      <Typography.Title level={3} style={{ margin: 0, fontSize: token.fontSizeHeading4 }}>
        {item.label}
      </Typography.Title>
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
        {item.description}
      </Typography.Paragraph>
      <Link href={item.href}>
        {item.linkLabel} <ArrowRightOutlined aria-hidden="true" />
      </Link>
    </Flex>
  );
}

export function FeatureCard({ item }: { item: AudienceItem }) {
  const { token } = theme.useToken();
  if (!item.demo) {
    return (
      <Card style={{ height: "100%" }}>
        <FeatureText item={item} />
      </Card>
    );
  }
  return (
    <Card styles={{ body: { padding: token.paddingLG } }}>
      <Row gutter={[token.marginLG, token.marginLG]} align="middle">
        <Col xs={24} lg={15}>
          <Image
            src={item.demo.src}
            alt={item.demo.alt}
            width={item.demo.width}
            height={item.demo.height}
            loading="lazy"
            unoptimized
            style={{
              display: "block",
              width: "100%",
              height: "auto",
              aspectRatio: `${item.demo.width} / ${item.demo.height}`,
              borderRadius: token.borderRadiusLG,
            }}
          />
        </Col>
        <Col xs={24} lg={9}>
          <FeatureText item={item} />
        </Col>
      </Row>
    </Card>
  );
}
