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

export function getGraphicsLabel(source) {
  const label = typeof source === 'string' ? source.toLowerCase() : '';
  if (/nvidia|nouveau/.test(label)) return 'Gráficos NVIDIA';
  if (/amdgpu|radeon|\bamd\b/.test(label)) return 'Gráficos AMD (APU/GPU)';
  if (/i915|xe\b|intel/.test(label)) return 'Gráficos Intel (APU/GPU)';
  if (/apu|integrated|igpu/.test(label)) return 'APU integrada';
  return 'Gráficos (APU/GPU)';
}

export function thresholdOrDefault(value, fallback) {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function describeTelemetryFreshness(timestamp, now = Date.now()) {
  const sampleTime = Number(timestamp);
  if (!Number.isFinite(sampleTime) || sampleTime <= 0) {
    return { fresh: false, label: 'Aguardando a primeira amostra de telemetria.' };
  }
  const ageSeconds = Math.max(0, Math.floor(now / 1000 - sampleTime));
  const ageLabel = ageSeconds < 60 ? `${ageSeconds}s` : `${Math.floor(ageSeconds / 60)}min`;
  return {
    fresh: ageSeconds <= 15,
    label: ageSeconds <= 15
      ? `Amostra recente · coletada há ${ageLabel}`
      : `Telemetria sem atualização há ${ageLabel}`,
  };
}
