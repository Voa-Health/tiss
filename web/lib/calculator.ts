export function band(value: number, edges: number[], labels: string[]): string {
  const index = edges.findIndex((edge) => value <= edge);
  return labels[index < 0 ? labels.length - 1 : index];
}

export function calculatorBands(values: {
  faturamento: number;
  percentual: number;
  glosa: number;
  recorridas: number;
  valor_medio: number;
}) {
  return {
    faturamento: band(
      values.faturamento,
      [100_000, 500_000, 2_000_000, 10_000_000],
      ["ate_100k", "100k_500k", "500k_2m", "2m_10m", "acima_10m"],
    ),
    percentual: band(values.percentual, [2, 5, 10, 20], ["ate_2", "2_5", "5_10", "10_20", "acima_20"]),
    glosa: band(values.glosa, [2, 5, 10, 20], ["ate_2", "2_5", "5_10", "10_20", "acima_20"]),
    recorridas: band(values.recorridas, [25, 50, 75], ["ate_25", "25_50", "50_75", "acima_75"]),
    valor_medio: band(values.valor_medio, [100, 300, 1_000], ["ate_100", "100_300", "300_1000", "acima_1000"]),
  };
}
