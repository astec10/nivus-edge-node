import assert from 'node:assert/strict';
import test from 'node:test';
import {
  NODE_HISTORY_QUERY_LIMIT,
  getNodeTelemetryIndicators,
  getNodeTelemetryQueryParams,
  normalizeNodeTelemetryBatches,
  summarizeNodeTelemetry,
} from '../src/utils/nodeTelemetryHistory.js';

const receivedAt = '2026-11-21T12:00:00.000Z';
const observedAt = '2026-11-21T11:59:58.500Z';

test('normalizes synthetic CPU, memory and disk samples without merging source and receive times', () => {
  const rows = normalizeNodeTelemetryBatches([{
    node_id: 'synthetic-node',
    schema_version: 1,
    received_at: receivedAt,
    observed_at: observedAt,
    clock_skew_seconds: 1.5,
    samples: [
      { metric: 'cpu.utilization', value: 42.5, unit: 'percent', quality: 'measured' },
      { metric: 'memory.utilization', value: 67, unit: 'percent', quality: 'estimated' },
      { metric: 'disk.utilization', value: null, unit: 'percent', quality: 'unavailable' },
    ],
  }]);

  assert.equal(rows.length, 1);
  assert.equal(rows[0].receivedAt, receivedAt);
  assert.equal(rows[0].observedAt, observedAt);
  assert.equal(rows[0].cpuPercent, 42.5);
  assert.equal(rows[0].cpuPercentQuality, 'measured');
  assert.equal(rows[0].memoryPercent, 67);
  assert.equal(rows[0].memoryPercentQuality, 'estimated');
  assert.equal(rows[0].diskPercent, null);
  assert.equal(rows[0].diskPercentQuality, 'unavailable');
});

test('keeps missing and non-numeric readings unavailable instead of inventing values', () => {
  const rows = normalizeNodeTelemetryBatches([{
    received_at: receivedAt,
    observed_at: observedAt,
    samples: [
      { metric: 'cpu.utilization', value: true, unit: 'percent', quality: 'measured' },
    ],
  }]);

  assert.equal(rows[0].cpuPercent, null);
  assert.equal(rows[0].cpuPercentQuality, 'unavailable');
  assert.equal(rows[0].memoryPercent, null);
  assert.equal(rows[0].memoryPercentQuality, 'unavailable');
  assert.equal(rows[0].diskPercent, null);
  assert.equal(rows[0].diskPercentQuality, 'unavailable');
});

test('drops batches without a valid received time and treats non-array payloads as empty', () => {
  assert.deepEqual(normalizeNodeTelemetryBatches(null), []);
  assert.deepEqual(normalizeNodeTelemetryBatches([{ received_at: 'not-a-date', samples: [] }]), []);
});

test('bounds every request to 500 batches and calculates the selected range from the supplied Master time', () => {
  const referenceNow = Date.parse('2026-11-21T12:00:00.000Z');
  assert.deepEqual(getNodeTelemetryQueryParams('1h', referenceNow), {
    limit: NODE_HISTORY_QUERY_LIMIT,
    since: '2026-11-21T11:00:00.000Z',
  });
  assert.deepEqual(getNodeTelemetryQueryParams('14d', referenceNow), {
    limit: NODE_HISTORY_QUERY_LIMIT,
    since: '2026-11-07T12:00:00.000Z',
  });
});

test('summarizes only finite numeric telemetry values', () => {
  const rows = normalizeNodeTelemetryBatches([
    {
      received_at: '2026-11-21T12:00:00.000Z',
      observed_at: observedAt,
      samples: [{ metric: 'cpu.utilization', value: 20, unit: 'percent', quality: 'measured' }],
    },
    {
      received_at: '2026-11-21T12:00:30.000Z',
      observed_at: observedAt,
      samples: [{ metric: 'cpu.utilization', value: 35, unit: 'percent', quality: 'measured' }],
    },
  ]);

  assert.deepEqual(summarizeNodeTelemetry(rows, 'cpuPercent'), {
    minimum: 20,
    maximum: 35,
    latest: 35,
  });
  assert.deepEqual(summarizeNodeTelemetry(rows, 'memoryPercent'), {
    minimum: null,
    maximum: null,
    latest: null,
  });
});

test('flags stale data and large observed-to-received time differences', () => {
  const latestReceived = Date.parse(receivedAt);
  const rows = [{ receivedMs: latestReceived, clockSkewSeconds: 61 }];
  assert.deepEqual(getNodeTelemetryIndicators(rows, latestReceived + 91_000), {
    latestAgeSeconds: 91,
    stale: true,
    hasClockSkew: true,
  });
  assert.deepEqual(getNodeTelemetryIndicators(
    [{ receivedMs: latestReceived, clockSkewSeconds: 60 }],
    latestReceived + 90_000,
  ), {
    latestAgeSeconds: 90,
    stale: false,
    hasClockSkew: false,
  });
});
