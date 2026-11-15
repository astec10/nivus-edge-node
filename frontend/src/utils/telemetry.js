export const CHART_RANGES = [
  { key: '5m', label: '5 min', minutes: 5 },
  { key: '15m', label: '15 min', minutes: 15 },
  { key: '30m', label: '30 min', minutes: 30 },
  { key: '60m', label: '1 hora', minutes: 60 },
  { key: 'all', label: 'Todas (até 1000)', minutes: null },
];

export function selectTelemetryWindow(samples, rangeKey) {
  const range = CHART_RANGES.find((item) => item.key === rangeKey) || CHART_RANGES[1];
  if (range.minutes === null) return samples;

  const latestTimestamp = samples.at(-1)?.timestamp;
  if (!Number.isFinite(latestTimestamp)) return [];

  const cutoff = latestTimestamp - range.minutes * 60;
  return samples.filter((sample) => Number.isFinite(sample.timestamp) && sample.timestamp >= cutoff);
}

export function summarizeMetric(samples, key) {
  const values = samples
    .map((sample) => sample?.[key])
    .filter((value) => typeof value === 'number' && Number.isFinite(value));
  const latest = samples.at(-1)?.[key];

  return {
    current: typeof latest === 'number' && Number.isFinite(latest) ? latest : null,
    minimum: values.length ? Math.min(...values) : null,
    maximum: values.length ? Math.max(...values) : null,
    count: values.length,
  };
}

export function formatMetric(value, unit = '') {
  return typeof value === 'number' && Number.isFinite(value)
    ? `${value.toFixed(1)}${unit}`
    : 'N/D';
}
