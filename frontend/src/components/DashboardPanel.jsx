import React, { useMemo, useState } from 'react';
import { Zap, Settings, Terminal } from 'lucide-react';
import MetricCard from './MetricCard';
import TelemetryChart from './TelemetryChart';
import { formatMetric, selectTelemetryWindow, summarizeMetric } from '../utils/telemetry';

const TEMPERATURE_METRICS = [
  { label: 'CPU / APU', key: 'temperature', source: 'temperature_source' },
  { label: 'GPU', key: 'gpu_temperature', source: 'gpu_temperature_source' },
  { label: 'GPU hotspot', key: 'gpu_hotspot_temperature', source: 'gpu_hotspot_source' },
  { label: 'Placa-mãe', key: 'motherboard_temperature', source: 'motherboard_temperature_source' },
];

function RangeDetails({ samples, metric, unit }) {
  const summary = summarizeMetric(samples, metric);
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '0.25rem 0.75rem', fontSize: '0.8rem' }}>
      <span>Atual</span><strong>{formatMetric(summary.current, unit)}</strong>
      <span>Mínima</span><strong>{formatMetric(summary.minimum, unit)}</strong>
      <span>Máxima</span><strong>{formatMetric(summary.maximum, unit)}</strong>
      <span>Amostras válidas</span><strong>{summary.count}</strong>
    </div>
  );
}

function TemperatureDetails({ samples }) {
  const latest = samples.at(-1);
  return (
    <div style={{ display: 'grid', gap: '0.65rem' }}>
      {TEMPERATURE_METRICS.map(({ label, key, source }) => {
        const summary = summarizeMetric(samples, key);
        return (
          <div key={key} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '0.15rem 0.6rem', borderBottom: '1px solid #334155', paddingBottom: '0.45rem' }}>
            <strong>{label}</strong><strong>{formatMetric(summary.current, '°C')}</strong>
            <small style={{ color: '#94a3b8' }}>Mín {formatMetric(summary.minimum, '°C')} · Máx {formatMetric(summary.maximum, '°C')}</small>
            <small style={{ gridColumn: '1 / -1', color: '#94a3b8' }}>Fonte: {latest?.[source] || 'sensor não exposto'}</small>
          </div>
        );
      })}
    </div>
  );
}

export default function DashboardPanel({ activeTab, error, latest, settings, setSettings, isAdmin, handleUpdateSetting, telemetry, controlMode, setControlMode, relayState, handleRelayToggle, systemLogs }) {
  const [chartMode, setChartMode] = useState('temperature');
  const [chartRange, setChartRange] = useState('15m');
  const chartRows = useMemo(() => selectTelemetryWindow(telemetry, chartRange), [telemetry, chartRange]);
  const temperatureDetails = <TemperatureDetails samples={chartRows} />;

  return (
    <>
      {activeTab === 'dashboard' && (
        <>
          {error && <div style={{ backgroundColor: '#7f1d1d', color: '#fca5a5', padding: '1rem', borderRadius: '0.5rem', marginBottom: '1.5rem' }}>{error}</div>}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(155px, 1fr))', gap: '1rem', marginBottom: '0.8rem' }}>
            <MetricCard label="CPU" value={formatMetric(latest?.cpu_percent, '%')} details={<RangeDetails samples={chartRows} metric="cpu_percent" unit="%" />} />
            <MetricCard label="Memória" value={formatMetric(latest?.memory_percent, '%')} details={<RangeDetails samples={chartRows} metric="memory_percent" unit="%" />} />
            <MetricCard label="Disco" value={formatMetric(latest?.disk_percent, '%')} details={<RangeDetails samples={chartRows} metric="disk_percent" unit="%" />} />
            <MetricCard label="CPU / APU" value={formatMetric(latest?.temperature_source ? latest.temperature : null, '°C')} hint={latest?.temperature_source || 'Fonte não identificada'} details={temperatureDetails} detailsLabel="Temperaturas por componente" />
            <MetricCard label="Placa-mãe" value={formatMetric(latest?.motherboard_temperature, '°C')} hint={latest?.motherboard_temperature_source || 'Sensor não exposto pelo SO/driver'} details={temperatureDetails} detailsLabel="Temperaturas por componente" />
            <MetricCard label="GPU" value={formatMetric(latest?.gpu_temperature, '°C')} hint={latest?.gpu_temperature_source || 'Sensor não exposto pelo SO/driver'} details={temperatureDetails} detailsLabel="Temperaturas por componente" />
            <MetricCard label="GPU hotspot" value={formatMetric(latest?.gpu_hotspot_temperature, '°C')} hint={latest?.gpu_hotspot_source || 'Sensor não exposto pelo SO/driver'} details={temperatureDetails} detailsLabel="Temperaturas por componente" />
            <MetricCard label="Energia estimada" value={formatMetric(latest?.power_consumption, ' W')} hint="Estimativa de software; não é medição física" details={<RangeDetails samples={chartRows} metric="power_consumption" unit=" W" />} />
          </div>

          <div style={{ color: '#94a3b8', fontSize: '0.78rem', margin: '0 0 1.25rem' }}>
            Para ver fonte e extremos térmicos, mantenha o ponteiro sobre um cartão de temperatura por 3 segundos. A janela usada acompanha o período do gráfico.
          </div>

          <TelemetryChart rows={chartRows} mode={chartMode} setMode={setChartMode} range={chartRange} setRange={setChartRange} />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '2rem', marginBottom: '2rem' }}>
            <div style={{ backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.75rem', border: '1px solid #334155' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ margin: 0, color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Zap size={18} style={{ color: '#eab308' }} /> Atuadores (MQTT)
                </h3>
                <div style={{ display: 'flex', backgroundColor: '#0f172a', borderRadius: '0.375rem', padding: '0.2rem', border: '1px solid #334155' }}>
                  <button onClick={() => setControlMode('auto')} style={{ backgroundColor: controlMode === 'auto' ? '#3b82f6' : 'transparent', color: 'white', border: 'none', padding: '0.3rem 0.7rem', borderRadius: '0.25rem', fontSize: '0.8rem', cursor: 'pointer', fontWeight: '600' }}>Auto</button>
                  <button onClick={() => setControlMode('manual')} style={{ backgroundColor: controlMode === 'manual' ? '#3b82f6' : 'transparent', color: 'white', border: 'none', padding: '0.3rem 0.7rem', borderRadius: '0.25rem', fontSize: '0.8rem', cursor: 'pointer', fontWeight: '600' }}>Manual</button>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#0f172a', padding: '1rem', borderRadius: '0.5rem', border: '1px solid #334155' }}>
                <div>
                  <div style={{ fontWeight: '500', fontSize: '0.95rem' }}>Relé Principal (Carga)</div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{controlMode === 'auto' ? 'Modo Automático ativo' : 'Modo Manual ativo'}</div>
                </div>
                <div onClick={controlMode === 'manual' && isAdmin ? handleRelayToggle : undefined} style={{ width: '56px', height: '28px', backgroundColor: relayState ? '#10b981' : '#475569', borderRadius: '14px', position: 'relative', cursor: controlMode === 'manual' && isAdmin ? 'pointer' : 'not-allowed', transition: 'background-color 0.2s', opacity: controlMode === 'auto' ? 0.6 : 1 }}>
                  <div style={{ width: '22px', height: '22px', backgroundColor: 'white', borderRadius: '50%', position: 'absolute', top: '3px', left: relayState ? '31px' : '3px', transition: 'left 0.2s', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }} />
                </div>
              </div>
            </div>

            <div style={{ backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.75rem', border: '1px solid #334155' }}>
              <h3 style={{ marginTop: 0, color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Settings size={18} /> Limiares de Alerta
              </h3>
              <div style={{ marginBottom: '0.5rem' }}>
                <label style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Temperatura Limite (°C):</label>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.3rem' }}>
                  <input type="number" disabled={!isAdmin} value={settings.temp_threshold} onChange={e => setSettings({ ...settings, temp_threshold: e.target.value })} style={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: 'white', padding: '0.4rem', borderRadius: '0.375rem', width: '100%' }} />
                  {isAdmin && <button onClick={() => handleUpdateSetting('temp_threshold', settings.temp_threshold)} style={{ backgroundColor: '#a855f7', color: 'white', border: 'none', padding: '0.4rem 0.8rem', borderRadius: '0.375rem', cursor: 'pointer' }}>Salvar</button>}
                </div>
              </div>
            </div>
          </div>

          <div style={{ backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.75rem', border: '1px solid #334155' }}>
            <h3 style={{ marginTop: 0, color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Terminal size={18} /> Logs do Sistema
            </h3>
            <div style={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '0.5rem', padding: '1rem', height: '160px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.85rem', color: '#38bdf8' }}>
              {systemLogs.map((log, i) => <div key={i}>{log}</div>)}
            </div>
          </div>
        </>
      )}
    </>
  );
}
