export const NODE_HISTORY_QUERY_LIMIT = 500;
export const NODE_HISTORY_MAX_OFFSET = 14 * 24 * 60 * 60 / 30;
export const NODE_HISTORY_STALE_AFTER_SECONDS = 90;
export const NODE_HISTORY_CLOCK_SKEW_WARNING_SECONDS = 60;

export const NODE_HISTORY_RANGES = [
  { key: '5m', label: '5 min', milliseconds: 5 * 60 * 1000 },
  { key: '15m', label: '15 min', milliseconds: 15 * 60 * 1000 },
  { key: '30m', label: '30 min', milliseconds: 30 * 60 * 1000 },
  { key: '1h', label: '1 hora', milliseconds: 60 * 60 * 1000 },
  { key: '6h', label: '6 horas', milliseconds: 6 * 60 * 60 * 1000 },
  { key: '24h', label: '24 horas', milliseconds: 24 * 60 * 60 * 1000 },
  { key: '14d', label: '14 dias', milliseconds: 14 * 24 * 60 * 60 * 1000 },
];

export const NODE_HISTORY_SERIES = [
  { metric: 'cpu.utilization', key: 'cpuPercent', label: 'CPU', unit: '%', color: '#38bdf8' },
  { metric: 'memory.utilization', key: 'memoryPercent', label: 'Memória', unit: '%', color: '#a78bfa' },
  { metric: 'disk.utilization', key: 'diskPercent', label: 'Disco', unit: '%', color: '#34d399' },
];

export const NODE_HISTORY_QUALITY_LABELS = {
  measured: 'Medido',
  estimated: 'Estimado',
  unavailable: 'Indisponível',
};

export function normalizeNodeTelemetryBatches(batches) {
  if (!Array.isArray(batches)) return [];
  return batches.map((batch) => {
    if (!batch || typeof batch !== 'object') return null;
    const receivedMs = Date.parse(batch.received_at);
    if (!Number.isFinite(receivedMs)) return null;
    const row = {
      receivedMs,
      receivedAt: batch.received_at,
      observedAt: batch.observed_at,
      clockSkewSeconds: typeof batch.clock_skew_seconds === 'number'
        && Number.isFinite(batch.clock_skew_seconds)
        ? batch.clock_skew_seconds
        : null,
    };
    const samples = Array.isArray(batch.samples) ? batch.samples : [];
    NODE_HISTORY_SERIES.forEach((series) => {
      const sample = samples.find((item) => item && item.metric === series.metric);
      const numericValue = sample && typeof sample.value === 'number'
        && Number.isFinite(sample.value)
        ? sample.value
        : null;
      const quality = sample && NODE_HISTORY_QUALITY_LABELS[sample.quality]
        ? sample.quality
        : 'unavailable';
      const hasValue = quality !== 'unavailable' && numericValue !== null;
      row[series.key] = hasValue ? numericValue : null;
      row[series.key + 'Quality'] = hasValue ? quality : 'unavailable';
    });
    return row;
  }).filter(Boolean);
}

export function getNodeTelemetryQueryParams(rangeKey, referenceNowMs = Date.now(), offset = 0, snapshotUntil = null) {
  const validOffset = Number.isSafeInteger(offset) && offset >= 0
    ? Math.min(offset, NODE_HISTORY_MAX_OFFSET)
    : 0;
  const params = { limit: NODE_HISTORY_QUERY_LIMIT, offset: validOffset };
  const selectedRange = NODE_HISTORY_RANGES.find((item) => item.key === rangeKey);
  if (selectedRange && Number.isFinite(referenceNowMs)) {
    params.since = new Date(referenceNowMs - selectedRange.milliseconds).toISOString();
  }
  if (typeof snapshotUntil === 'string' && Number.isFinite(Date.parse(snapshotUntil))) {
    params.snapshot_until = snapshotUntil;
  }
  return params;
}

function readHeader(headers, name) {
  if (headers && typeof headers.get === 'function') {
    const value = headers.get(name);
    if (value !== null && value !== undefined) return value;
  }
  return headers && (headers[name] ?? headers[name.toLowerCase()]);
}

function parseNonNegativeInteger(value, fallback = null) {
  if (value === null || value === undefined || value === '') return fallback;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : fallback;
}

export function getNodeTelemetryPageMetadata(headers = {}, fallbackCount = 0) {
  const supported = String(readHeader(headers, 'X-Nivus-History-Pagination') || '').toLowerCase() === 'offset-v1';
  return {
    supported,
    totalBatches: parseNonNegativeInteger(readHeader(headers, 'X-Nivus-History-Total-Batches')),
    offset: parseNonNegativeInteger(readHeader(headers, 'X-Nivus-History-Offset'), 0),
    limit: parseNonNegativeInteger(readHeader(headers, 'X-Nivus-History-Limit'), NODE_HISTORY_QUERY_LIMIT),
    hasMore: String(readHeader(headers, 'X-Nivus-History-Has-More') || '').toLowerCase() === 'true',
    rangeStart: readHeader(headers, 'X-Nivus-History-Range-Start') || null,
    rangeEnd: readHeader(headers, 'X-Nivus-History-Range-End') || null,
    snapshotUntil: readHeader(headers, 'X-Nivus-History-Snapshot-Until') || null,
    fallbackCount,
  };
}

export function summarizeNodeTelemetry(rows, key) {
  const values = rows
    .map((row) => row[key])
    .filter((value) => typeof value === 'number' && Number.isFinite(value));
  if (!values.length) return { minimum: null, maximum: null, latest: null };
  return {
    minimum: Math.min(...values),
    maximum: Math.max(...values),
    latest: values[values.length - 1],
  };
}

export function getNodeTelemetryIndicators(rows, referenceNowMs) {
  const latest = rows.length ? rows[rows.length - 1] : null;
  const latestAgeSeconds = latest && Number.isFinite(referenceNowMs)
    ? (referenceNowMs - latest.receivedMs) / 1000
    : null;
  return {
    latestAgeSeconds,
    stale: Number.isFinite(latestAgeSeconds)
      && latestAgeSeconds > NODE_HISTORY_STALE_AFTER_SECONDS,
    hasClockSkew: rows.some((row) => row.clockSkewSeconds !== null
      && Math.abs(row.clockSkewSeconds) > NODE_HISTORY_CLOCK_SKEW_WARNING_SECONDS),
  };
}
