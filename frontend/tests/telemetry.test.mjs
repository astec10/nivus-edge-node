import assert from 'node:assert/strict';
import { selectTelemetryWindow, summarizeMetric } from '../src/utils/telemetry.js';

const samples = [
  { timestamp: 100, temperature: 52, gpu_hotspot_temperature: 61 },
  { timestamp: 200, temperature: 55, gpu_hotspot_temperature: null },
  { timestamp: 400, temperature: 57, gpu_hotspot_temperature: 68 },
  { timestamp: 500, temperature: null, gpu_hotspot_temperature: null },
];

assert.equal(selectTelemetryWindow(samples, '5m').length, 3);
assert.equal(selectTelemetryWindow(samples, 'all').length, 4);
assert.equal(summarizeMetric(samples, 'temperature').current, null);
assert.equal(summarizeMetric(samples, 'temperature').minimum, 52);
assert.equal(summarizeMetric(samples, 'temperature').maximum, 57);
assert.equal(summarizeMetric(samples, 'temperature').count, 3);
assert.equal(summarizeMetric(samples, 'gpu_hotspot_temperature').maximum, 68);
assert.equal(summarizeMetric(samples, 'motherboard_temperature').current, null);

console.log('Telemetry range and missing-sensor summaries passed.');
