import React, { useEffect, useMemo, useState } from 'react';
import { Activity } from 'lucide-react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { CHART_RANGES, formatMetric, summarizeMetric } from '../utils/telemetry';

const CHARTS = {
  temperature: {
    title: 'Temperaturas por componente',
    unit: '°C',
    series: [
      { key: 'temperature', name: 'CPU / APU', color: '#f87171', source: 'temperature_source' },
      { key: 'motherboard_temperature', name: 'Placa-mãe', color: '#a78bfa', source: 'motherboard_temperature_source' },
      { key: 'gpu_temperature', name: 'GPU', color: '#38bdf8', source: 'gpu_temperature_source' },
      { key: 'gpu_hotspot_temperature', name: 'GPU hotspot', color: '#fb923c', source: 'gpu_hotspot_source' },
    ],
  },
  performance: {
    title: 'Uso de recursos',
    unit: '%',
    series: [
      { key: 'cpu_percent', name: 'CPU (%)', color: '#38bdf8' },
      { key: 'memory_percent', name: 'Memória (%)', color: '#a78bfa' },
      { key: 'disk_percent', name: 'Disco (%)', color: '#34d399' },
    ],
  },
  energy: {
    title: 'Consumo estimado',
    unit: ' W',
    series: [
      { key: 'power_consumption', name: 'Potência estimada (W)', color: '#34d399' },
    ],
  },
};

function DelayedChartTooltip({ active, payload, mode, rows }) {
  const [ready, setReady] = useState(false);
  const sample = payload?.[0]?.payload;
  const sampleKey = sample?.timestamp ?? sample?.time;

  useEffect(() => {
    setReady(false);
    if (!active || sampleKey == null) return undefined;
    const timer = window.setTimeout(() => setReady(true), 3000);
    return () => window.clearTimeout(timer);
  }, [active, sampleKey, mode]);

  if (!active || !ready || !sample) return null;
  const series = CHARTS[mode].series;

  return (
    <div style={{ minWidth: 230, padding: '0.8rem', border: '1px solid #475569', borderRadius: '0.6rem', background: '#07111f', color: '#f8fafc', boxShadow: '0 8px 24px #0008' }}>
      <strong style={{ display: 'block', marginBottom: '0.45rem' }}>{sample.time || 'Amostra'}</strong>
      {series.map(({ key, name, color, source }) => {
        const point = formatMetric(sample[key], mode === 'energy' ? ' W' : mode === 'temperature' ? '°C' : '%');
        const summary = summarizeMetric(rows, key);
        return (
          <div key={key} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '0.8rem', fontSize: '0.78rem', marginTop: '0.25rem' }}>
            <span style={{ color }}>{name}</span>
            <span>{point}</span>
            {summary.count > 0 && <small style={{ gridColumn: '1 / -1', color: '#94a3b8' }}>Mín {formatMetric(summary.minimum, mode === 'energy' ? ' W' : mode === 'temperature' ? '°C' : '%')} · Máx {formatMetric(summary.maximum, mode === 'energy' ? ' W' : mode === 'temperature' ? '°C' : '%')} no período</small>}
            {source && <small style={{ gridColumn: '1 / -1', color: '#94a3b8' }}>Fonte: {sample[source] || 'sensor não exposto'}</small>}
          </div>
        );
      })}
      {mode === 'temperature' && (
        <div style={{ borderTop: '1px solid #334155', marginTop: '0.55rem', paddingTop: '0.45rem', fontSize: '0.72rem', color: '#cbd5e1' }}>
          Tooltip detalhado após 3 segundos sobre o ponto.
        </div>
      )}
    </div>
  );
}

export default function TelemetryChart({ rows, mode, setMode, range, setRange }) {
  const chart = CHARTS[mode];
  const summaries = useMemo(
    () => Object.fromEntries(chart.series.map(({ key }) => [key, summarizeMetric(rows, key)])),
    [chart, rows],
  );
  const hasValues = chart.series.some(({ key }) => summaries[key].count > 0);

  const chartModes = [
    { key: 'temperature', label: 'Temperaturas' },
    { key: 'performance', label: 'Uso' },
    { key: 'energy', label: 'Energia' },
  ];

  return (
    <section style={{ backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.75rem', border: '1px solid #334155', marginBottom: '2rem' }} aria-labelledby="telemetry-chart-title">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap' }}>
        <h3 id="telemetry-chart-title" style={{ margin: 0, color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Activity style={{ color: '#38bdf8' }} /> {chart.title}
        </h3>
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }} role="group" aria-label="Tipo de gráfico">
          {chartModes.map((option) => (
            <button key={option.key} type="button" aria-pressed={mode === option.key} onClick={() => setMode(option.key)} style={{ background: mode === option.key ? '#0e7490' : '#0f172a', color: '#f8fafc', border: '1px solid #475569', borderRadius: '0.45rem', padding: '0.42rem 0.65rem', cursor: 'pointer' }}>
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.8rem', flexWrap: 'wrap', marginTop: '0.8rem' }}>
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }} role="group" aria-label="Período do gráfico">
          {CHART_RANGES.map((option) => (
            <button key={option.key} type="button" aria-pressed={range === option.key} onClick={() => setRange(option.key)} style={{ background: range === option.key ? '#1d4ed8' : '#0f172a', color: '#e2e8f0', border: '1px solid #475569', borderRadius: '0.45rem', padding: '0.38rem 0.6rem', cursor: 'pointer', fontSize: '0.82rem' }}>
              {option.label}
            </button>
          ))}
        </div>
        <small style={{ color: '#94a3b8' }}>{rows.length} amostras no período · histórico limitado às 1000 mais recentes</small>
      </div>

      <div style={{ width: '100%', height: 330, marginTop: '0.9rem' }}>
        {hasValues ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows} margin={{ top: 8, right: 12, left: 0, bottom: 6 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" stroke="#94a3b8" minTickGap={24} />
              <YAxis stroke="#94a3b8" unit={chart.unit} domain={mode === 'performance' ? [0, 100] : ['auto', 'auto']} width={60} />
              <Tooltip content={<DelayedChartTooltip mode={mode} rows={rows} />} />
              <Legend />
              {chart.series.map(({ key, name, color }) => (
                <Line key={key} type="monotone" dataKey={key} name={name} stroke={color} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ height: '100%', display: 'grid', placeItems: 'center', padding: '1rem', color: '#94a3b8', textAlign: 'center' }}>
            {mode === 'temperature' ? 'Nenhuma temperatura identificada neste período. Leituras antigas sem origem não são reutilizadas.' : 'Sem amostras para este período.'}
          </div>
        )}
      </div>
    </section>
  );
}
