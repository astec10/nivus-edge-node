import assert from 'node:assert/strict';
import { describeTelemetryFreshness, getGraphicsLabel, selectTelemetryWindow, summarizeMetric, thresholdOrDefault } from '../src/utils/telemetry.js';

const samples = [
  { timestamp: 100, temperature: 52, gpu_hotspot_temperature: 61 },
  { timestamp: 200, temperature: 55, gpu_hotspot_temperature: null },
  { timestamp: 400, temperature: 57, gpu_hotspot_temperature: 68 },
  { timestamp: 500, temperature: null, cpu_hotspot_temperature: null, gpu_hotspot_temperature: null },
];

assert.equal(selectTelemetryWindow(samples, '5m').length, 3);
assert.equal(selectTelemetryWindow(samples, 'all').length, 4);
assert.equal(summarizeMetric(samples, 'temperature').current, null);
assert.equal(summarizeMetric(samples, 'temperature').minimum, 52);
assert.equal(summarizeMetric(samples, 'temperature').maximum, 57);
assert.equal(summarizeMetric(samples, 'temperature').count, 3);
assert.equal(summarizeMetric(samples, 'gpu_hotspot_temperature').maximum, 68);
assert.equal(summarizeMetric(samples, 'cpu_hotspot_temperature').current, null);
assert.equal(summarizeMetric(samples, 'motherboard_temperature').current, null);
assert.equal(getGraphicsLabel('amdgpu: edge'), 'Gráficos AMD (APU/GPU)');
assert.equal(getGraphicsLabel('nvidia: temp1'), 'Gráficos NVIDIA');
assert.equal(getGraphicsLabel(null), 'Gráficos (APU/GPU)');
assert.equal(thresholdOrDefault('0', 75), 0);
assert.equal(thresholdOrDefault('invalid', 75), 75);
assert.equal(describeTelemetryFreshness(1, 10000).fresh, true);
assert.equal(describeTelemetryFreshness(1, 10000).label, 'Amostra recente · coletada há 9s');
assert.equal(describeTelemetryFreshness(1, 30000).fresh, false);
assert.equal(describeTelemetryFreshness(null, 30000).label, 'Aguardando a primeira amostra de telemetria.');

console.log('Telemetry ranges, freshness, sensor labels, missing-sensor summaries, and threshold parsing passed.');
