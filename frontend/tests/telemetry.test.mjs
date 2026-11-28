import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
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

const vite = await createServer({
  root: path.resolve(fileURLToPath(new URL('..', import.meta.url))),
  server: { middlewareMode: true },
  appType: 'custom',
});
try {
  const { CpuDetails, parseCpuPerCoreUsage, summarizeCpuPerCore } = await vite.ssrLoadModule('/src/components/DashboardPanel.jsx');
  assert.deepEqual(parseCpuPerCoreUsage('[12.5, 100, null]'), [12.5, 100, null]);
  assert.deepEqual(parseCpuPerCoreUsage('[true, -1, 101, "45", null]'), [null, null, null, null, null]);
  assert.deepEqual(parseCpuPerCoreUsage('not-json'), []);
  assert.deepEqual(parseCpuPerCoreUsage(JSON.stringify(Array(257).fill(1))), []);

  const cpuSamples = [
    { cpu_percent: 30, cpu_per_core_json: '[10, 80]', cpu_source: 'psutil.cpu_percent', cpu_per_core_source: 'psutil.cpu_percent(percpu=True)' },
    { cpu_percent: 40, cpu_per_core_json: '[20, 60, 100]', cpu_source: 'psutil.cpu_percent', cpu_per_core_source: 'psutil.cpu_percent(percpu=True)' },
  ];
  assert.deepEqual(summarizeCpuPerCore(cpuSamples), [
    { index: 0, current: 20, minimum: 10, maximum: 20, count: 2 },
    { index: 1, current: 60, minimum: 60, maximum: 80, count: 2 },
    { index: 2, current: 100, minimum: 100, maximum: 100, count: 1 },
  ]);
  const details = renderToStaticMarkup(React.createElement(CpuDetails, { samples: cpuSamples }));
  assert.match(details, /Uso agregado/);
  assert.match(details, /CPU 0/);
  assert.match(details, /CPU 2/);
  assert.ok(details.includes('Fonte: psutil.cpu_percent(percpu=True)'));
  assert.match(renderToStaticMarkup(React.createElement(CpuDetails, { samples: [{ cpu_percent: 25 }] })), /Uso por CPU lógico/);
} finally {
  await vite.close();
}

console.log('Telemetry ranges, freshness, sensor labels, CPU-core details, and threshold parsing passed.');
