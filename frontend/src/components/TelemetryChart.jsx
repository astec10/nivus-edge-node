import React, { useEffect, useMemo, useState } from 'react';
import { Activity } from 'lucide-react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { CHART_RANGES, formatMetric, getGraphicsLabel, summarizeMetric } from '../utils/telemetry';

const CHARTS = {
  all: {
    title: 'Visão conjunta de telemetria',
    series: [
      { key: 'temperature', name: 'CPU (°C)', unit: '°C', color: '#f87171', source: 'temperature_source' },
      { key: 'motherboard_temperature', name: 'Placa-mãe (°C)', unit: '°C', color: '#a78bfa', source: 'motherboard_temperature_source' },
      { key: 'gpu_temperature', name: 'Gráficos (°C)', unit: '°C', color: '#38bdf8', source: 'gpu_temperature_source' },
      { key: 'cpu_percent', name: 'CPU (%)', unit: '%', color: '#fbbf24' },
      { key: 'memory_percent', name: 'Memória (%)', unit: '%', color: '#c084fc' },
      { key: 'disk_percent', name: 'Disco (%)', unit: '%', color: '#34d399' },
      { key: 'power_consumption', name: 'Potência estimada (W)', unit: ' W', color: '#fb923c' },
    ],
  },
  temperature: {
    title: 'Temperaturas por componente',
    series: [
      { key: 'temperature', name: 'CPU (pacote)', unit: '°C', color: '#f87171', source: 'temperature_source' },
      { key: 'motherboard_temperature', name: 'Placa-mãe', unit: '°C', color: '#a78bfa', source: 'motherboard_temperature_source' },
      { key: 'gpu_temperature', name: 'Gráficos (APU/GPU)', unit: '°C', color: '#38bdf8', source: 'gpu_temperature_source' },
    ],
  },
  performance: {
    title: 'Uso de recursos',
    series: [
      { key: 'cpu_percent', name: 'CPU', unit: '%', color: '#38bdf8' },
      { key: 'memory_percent', name: 'Memória', unit: '%', color: '#a78bfa' },
      { key: 'disk_percent', name: 'Disco', unit: '%', color: '#34d399' },
    ],
  },
  energy: {
    title: 'Consumo estimado',
    series: [
      { key: 'power_consumption', name: 'Potência estimada', unit: ' W', color: '#34d399' },
    ],
  },
};

const HOTSPOT_DETAILS = [
  { key: 'cpu_hotspot_temperature', name: 'CPU hotspot', unit: '°C', source: 'cpu_hotspot_source' },
  { key: 'gpu_hotspot_temperature', name: 'GPU hotspot', unit: '°C', source: 'gpu_hotspot_source' },
];

const CHART_MODES = [
  { key: 'all', label: 'Tudo' },
  { key: 'temperature', label: 'Temperaturas' },
  { key: 'performance', label: 'Uso' },
  { key: 'energy', label: 'Energia' },
];

const CHART_TYPES = [
  { key: 'line', label: 'Linha' },
  { key: 'area', label: 'Área' },
  { key: 'bar', label: 'Barras' },
];

function DelayedChartTooltip({ active, payload, series, rows, selectionKey, mode }) {
  const [ready, setReady] = useState(false);
  const sample = payload?.[0]?.payload;
  const sampleKey = sample?.timestamp ?? sample?.time;

  useEffect(() => {
    setReady(false);
    if (!active || sampleKey == null) return undefined;
    const timer = window.setTimeout(() => setReady(true), 3000);
    return () => window.clearTimeout(timer);
  }, [active, sampleKey, selectionKey, mode]);

  if (!active || !sample) return null;

  return (
    <div className="telemetry-chart-tooltip">
      <strong>{sample.time || 'Amostra'}</strong>
      {series.map(({ key, name, color, unit, source }) => {
        const summary = summarizeMetric(rows, key);
        return (
          <div key={key} className="telemetry-chart-tooltip-row">
            <span style={{ color }}>{name}</span>
            <strong>{formatMetric(sample[key], unit)}</strong>
            {ready && summary.count > 0 && (
              <small className="telemetry-chart-tooltip-meta">
                Mín {formatMetric(summary.minimum, unit)} · Máx {formatMetric(summary.maximum, unit)} no período
              </small>
            )}
            {ready && source && <small className="telemetry-chart-tooltip-meta">Fonte: {sample[source] || 'sensor não exposto'}</small>}
          </div>
        );
      })}
      {ready && (mode === 'all' || mode === 'temperature') && HOTSPOT_DETAILS.map(({ key, name, unit, source }) => {
        const summary = summarizeMetric(rows, key);
        return (
          <div key={key} className="telemetry-chart-tooltip-row telemetry-chart-tooltip-detail">
            <span>{name} · detalhe</span>
            <strong>{formatMetric(sample[key], unit)}</strong>
            {ready && summary.count > 0 && (
              <small className="telemetry-chart-tooltip-meta">
                Mín {formatMetric(summary.minimum, unit)} · Máx {formatMetric(summary.maximum, unit)} no período
              </small>
            )}
            <small className="telemetry-chart-tooltip-meta">Fonte: {sample[source] || 'sensor não exposto'}</small>
          </div>
        );
      })}
    </div>
  );
}

function renderSeries(chartType, series) {
  const props = {
    key: series.key,
    dataKey: series.key,
    name: series.name,
    yAxisId: series.unit,
    stroke: series.color,
    fill: series.color,
    strokeWidth: 2,
    isAnimationActive: false,
  };

  if (chartType === 'area') return <Area {...props} type="monotone" fillOpacity={0.12} dot={false} connectNulls={false} />;
  if (chartType === 'bar') return <Bar {...props} />;
  return <Line {...props} type="monotone" dot={false} connectNulls={false} />;
}

export default function TelemetryChart({ rows, mode, setMode, range, setRange }) {
  const [chartType, setChartType] = useState('line');
  const [visibleKeys, setVisibleKeys] = useState(() => new Set(CHARTS[mode].series.map(({ key }) => key)));
  const graphicsLabel = getGraphicsLabel(rows.at(-1)?.gpu_temperature_source);
  const chart = useMemo(() => ({
    ...CHARTS[mode],
    series: CHARTS[mode].series.map((series) => (
      series.key === 'gpu_temperature'
        ? { ...series, name: `${graphicsLabel} (°C)` }
        : series
    )),
  }), [graphicsLabel, mode]);
  const selectedSeries = chart.series.filter(({ key }) => visibleKeys.has(key));
  const summaries = useMemo(
    () => Object.fromEntries(chart.series.map(({ key }) => [key, summarizeMetric(rows, key)])),
    [chart, rows],
  );
  const hasValues = selectedSeries.some(({ key }) => summaries[key].count > 0);
  const units = [...new Set(selectedSeries.map(({ unit }) => unit))];
  const selectionKey = selectedSeries.map(({ key }) => key).join(',');

  useEffect(() => {
    setVisibleKeys(new Set(CHARTS[mode].series.map(({ key }) => key)));
  }, [mode]);

  const toggleSeries = (key) => {
    setVisibleKeys((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const ChartComponent = chartType === 'area' ? AreaChart : chartType === 'bar' ? BarChart : LineChart;

  return (
    <section className="telemetry-chart-panel" aria-labelledby="telemetry-chart-title">
      <div className="telemetry-chart-heading">
        <h3 id="telemetry-chart-title"><Activity aria-hidden="true" /> {chart.title}</h3>
      </div>

      <div className="telemetry-chart-controls" aria-label="Controles do gráfico">
        <div className="telemetry-chart-control-group">
          <span className="telemetry-control-label">Dados</span>
          <div className="telemetry-chart-modes" role="group" aria-label="Conjunto de informações do gráfico">
            {CHART_MODES.map((option) => (
              <button key={option.key} type="button" aria-pressed={mode === option.key} onClick={() => setMode(option.key)}>
                {option.label}
              </button>
            ))}
          </div>
        </div>
        <div className="telemetry-chart-control-group">
          <span className="telemetry-control-label">Período</span>
          <div className="telemetry-chart-ranges" role="group" aria-label="Período do gráfico">
            {CHART_RANGES.map((option) => (
              <button key={option.key} type="button" aria-pressed={range === option.key} onClick={() => setRange(option.key)}>
                {option.label}
              </button>
            ))}
          </div>
        </div>
        <label className="telemetry-chart-type">
          <span className="telemetry-control-label">Tipo de gráfico</span>
          <select value={chartType} onChange={(event) => setChartType(event.target.value)} aria-label="Tipo de gráfico">
            {CHART_TYPES.map((option) => <option key={option.key} value={option.key}>{option.label}</option>)}
          </select>
        </label>
      </div>

      <div className="telemetry-series-toolbar">
        <div className="telemetry-series-heading">
          <span className="telemetry-control-label">Séries visíveis</span>
          <div className="telemetry-series-options" role="group" aria-label="Séries visíveis">
            {chart.series.map(({ key, name, color }) => (
            <button
              key={key}
              type="button"
              aria-pressed={visibleKeys.has(key)}
              onClick={() => toggleSeries(key)}
              className={visibleKeys.has(key) ? 'telemetry-series-selected' : ''}
              style={{ '--series-color': color }}
            >
              <span aria-hidden="true" />{name}
            </button>
            ))}
          </div>
        </div>
        <button
          className="telemetry-show-all"
          type="button"
          onClick={() => setVisibleKeys(new Set(chart.series.map(({ key }) => key)))}
        >
          Mostrar todas as informações
        </button>
      </div>

      <div className="telemetry-chart-caption">
        <small>{rows.length} amostras no período · até 1000 amostras armazenadas</small>
        {mode === 'all' && <small>°C, %, e W usam escalas próprias; a potência é estimada por software.</small>}
        <small>Valor do ponto imediato · mínimos, máximos, fonte e hotspot após 3 segundos.</small>
      </div>

      <div className="telemetry-chart-canvas">
        {hasValues ? (
          <ResponsiveContainer width="100%" height="100%">
            <ChartComponent data={rows} margin={{ top: 8, right: units.length > 1 ? 88 : 12, left: 0, bottom: 6 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" stroke="#94a3b8" minTickGap={24} />
              {units.map((unit, index) => (
                <YAxis
                  key={unit}
                  yAxisId={unit}
                  stroke="#94a3b8"
                  unit={unit}
                  domain={unit === '%' ? [0, 100] : ['auto', 'auto']}
                  width={unit === '°C' ? 48 : 42}
                  orientation={index === 0 ? 'left' : 'right'}
                  hide={false}
                  tick={{ fontSize: 11 }}
                  {...(index > 1 ? { orientation: 'right', width: 42, offset: 38, tick: { fontSize: 10 } } : {})}
                />
              ))}
              <Tooltip content={<DelayedChartTooltip series={selectedSeries} rows={rows} selectionKey={selectionKey} mode={mode} />} />
              {selectedSeries.map((series) => renderSeries(chartType, series))}
            </ChartComponent>
          </ResponsiveContainer>
        ) : (
          <div className="telemetry-chart-empty">
            {selectedSeries.length === 0
              ? 'Selecione uma ou mais séries para exibir.'
              : mode === 'temperature'
                ? 'Nenhuma temperatura identificada neste período. Leituras antigas sem origem não são reutilizadas.'
                : 'Sem amostras para as séries selecionadas neste período.'}
          </div>
        )}
      </div>
    </section>
  );
}
