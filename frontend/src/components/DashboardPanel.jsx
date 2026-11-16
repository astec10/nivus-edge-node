import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { Bell, Cpu, History, Settings, Terminal, Volume2, VolumeX, Zap } from 'lucide-react';
import MetricCard from './MetricCard';
import { describeTelemetryFreshness, formatMetric, getGraphicsLabel, selectTelemetryWindow, summarizeMetric } from '../utils/telemetry';

const TelemetryChart = lazy(() => import('./TelemetryChart'));

function MetricDetails({ samples, metrics }) {
  return (
    <div className="metric-details-list">
      {metrics.map(({ label, key, source }) => {
        const summary = summarizeMetric(samples, key);
        const latest = samples.at(-1);
        return (
          <div className="metric-details-item" key={key}>
            <strong>{label}</strong>
            <strong>{formatMetric(summary.current, '°C')}</strong>
            <small>Mín {formatMetric(summary.minimum, '°C')} · Máx {formatMetric(summary.maximum, '°C')}</small>
            <small>Fonte: {latest?.[source] || 'sensor não exposto pelo SO/driver'}</small>
          </div>
        );
      })}
    </div>
  );
}

function RangeDetails({ samples, metric, unit }) {
  const summary = summarizeMetric(samples, metric);
  return (
    <div className="metric-details-list">
      <div className="metric-details-item">
        <strong>Atual</strong><strong>{formatMetric(summary.current, unit)}</strong>
        <small>Mín {formatMetric(summary.minimum, unit)} · Máx {formatMetric(summary.maximum, unit)}</small>
        <small>{summary.count} amostras válidas no período</small>
      </div>
    </div>
  );
}

function formatDatabaseTimestamp(value) {
  if (!value) return 'Horário indisponível';
  const text = String(value);
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(text)
    ? text
    : `${text.replace(' ', 'T')}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? text : date.toLocaleString();
}

function alertDescription(alertType) {
  if (alertType === 'TEMPERATURE_HIGH') return { name: 'Temperatura CPU/APU', unit: '°C' };
  if (alertType === 'CPU_HIGH') return { name: 'Uso de CPU', unit: '%' };
  return { name: alertType || 'Alerta', unit: '' };
}

export default function DashboardPanel({
  activeTab,
  error,
  latest,
  settings,
  isAdmin,
  isTempCritical,
  handleUpdateSetting,
  telemetry,
  handleActuatorCommand,
  actuatorMessage,
  settingsStatus,
  soundEnabled,
  soundStatus,
  onToggleAlertSound,
  systemLogs,
  auditLogs,
  alertsHistory,
}) {
  const [chartMode, setChartMode] = useState('all');
  const [chartRange, setChartRange] = useState('15m');
  const [thresholdDraft, setThresholdDraft] = useState(settings.temp_threshold ?? '75');
  const [thresholdDirty, setThresholdDirty] = useState(false);
  const [savingThreshold, setSavingThreshold] = useState(false);
  const thresholdValue = Number.parseFloat(thresholdDraft);
  const thresholdValid = Number.isFinite(thresholdValue) && thresholdValue >= 0 && thresholdValue <= 150;
  const chartRows = useMemo(() => selectTelemetryWindow(telemetry, chartRange), [telemetry, chartRange]);

  useEffect(() => {
    if (!thresholdDirty) setThresholdDraft(settings.temp_threshold ?? '75');
  }, [settings.temp_threshold, thresholdDirty]);

  const saveThreshold = async () => {
    if (!thresholdValid) return;
    setSavingThreshold(true);
    const saved = await handleUpdateSetting('temp_threshold', String(thresholdValue));
    if (saved) {
      setThresholdDraft(String(thresholdValue));
      setThresholdDirty(false);
    }
    setSavingThreshold(false);
  };

  const temperatureSamples = chartRows;
  const graphicsLabel = getGraphicsLabel(latest?.gpu_temperature_source);
  const freshness = describeTelemetryFreshness(latest?.timestamp);

  return (
    <>
      {activeTab === 'dashboard' && (
        <main className="dashboard-content">
          {error && <div className="dashboard-error" role="alert">{error}</div>}

          <p className="dashboard-metric-help">
            Passe o ponteiro ou use o foco do teclado sobre um cartão por 3 segundos para ver fonte, mínimas e máximas. Os detalhes acompanham o período selecionado no gráfico.
          </p>
          <p className={`dashboard-telemetry-freshness ${freshness.fresh ? 'dashboard-telemetry-fresh' : 'dashboard-telemetry-stale'}`} role="status" aria-live="polite">
            {freshness.label}
            {latest?.timestamp && ` · ${formatDatabaseTimestamp(new Date(Number(latest.timestamp) * 1000).toISOString())}`}
          </p>
          {isTempCritical && (
            <div className="dashboard-temperature-alert" role="alert">
              Temperatura CPU/APU acima do limite configurado: {formatMetric(latest?.temperature, '°C')}.
            </div>
          )}

          <div className="dashboard-metric-grid">
            <MetricCard label="CPU" value={formatMetric(latest?.cpu_percent, '%')} details={<RangeDetails samples={chartRows} metric="cpu_percent" unit="%" />} />
            <MetricCard label="Memória" value={formatMetric(latest?.memory_percent, '%')} details={<RangeDetails samples={chartRows} metric="memory_percent" unit="%" />} />
            <MetricCard label="Disco" value={formatMetric(latest?.disk_percent, '%')} details={<RangeDetails samples={chartRows} metric="disk_percent" unit="%" />} />
            <MetricCard
              label="CPU / APU"
              value={formatMetric(latest?.temperature_source ? latest.temperature : null, '°C')}
              hint={latest?.temperature_source || 'Sensor térmico não exposto'}
              details={<MetricDetails samples={temperatureSamples} metrics={[
                { label: 'CPU / APU', key: 'temperature', source: 'temperature_source' },
                { label: 'CPU hotspot', key: 'cpu_hotspot_temperature', source: 'cpu_hotspot_source' },
              ]} />}
              detailsLabel="Temperatura de CPU / APU"
            />
            <MetricCard
              label={graphicsLabel}
              value={formatMetric(latest?.gpu_temperature, '°C')}
              hint={latest?.gpu_temperature_source || 'Sensor gráfico não exposto'}
              details={<MetricDetails samples={temperatureSamples} metrics={[
                { label: 'Gráficos (APU/GPU)', key: 'gpu_temperature', source: 'gpu_temperature_source' },
                { label: 'GPU hotspot', key: 'gpu_hotspot_temperature', source: 'gpu_hotspot_source' },
              ]} />}
              detailsLabel={`${graphicsLabel} · temperaturas`}
            />
            <MetricCard
              label="Placa-mãe"
              value={formatMetric(latest?.motherboard_temperature, '°C')}
              hint={latest?.motherboard_temperature_source || 'Sensor não exposto pelo SO/driver'}
              details={<MetricDetails samples={temperatureSamples} metrics={[{ label: 'Placa-mãe', key: 'motherboard_temperature', source: 'motherboard_temperature_source' }]} />}
              detailsLabel="Temperatura da placa-mãe"
            />
            <MetricCard
              label="Energia estimada"
              value={formatMetric(latest?.power_consumption, ' W')}
              hint="Estimativa de software; não é medição física"
              details={<RangeDetails samples={chartRows} metric="power_consumption" unit=" W" />}
            />
          </div>

          <Suspense fallback={<div className="telemetry-chart-loading" role="status">Carregando gráficos…</div>}>
            <TelemetryChart rows={chartRows} mode={chartMode} setMode={setChartMode} range={chartRange} setRange={setChartRange} />
          </Suspense>

          <div className="dashboard-secondary-grid">
            <section className="dashboard-panel" aria-labelledby="actuator-title">
              <div className="dashboard-panel-heading">
                <h3 id="actuator-title"><Zap aria-hidden="true" /> Atuador MQTT</h3>
                <span className="dashboard-panel-tag">Automação aguardando bateria</span>
              </div>
              <p className="dashboard-panel-copy">
                Regra definida: desligar <code>nivus/edge/relay1</code> quando a bateria do dispositivo móvel associado estiver em 20% ou menos. A telemetria ainda não fornece esse nível; até a origem ser integrada, os comandos abaixo continuam manuais.
              </p>
              <div className="actuator-command-row">
                <div>
                  <strong>Relé principal</strong>
                  <small>Tópico: nivus/edge/relay1</small>
                </div>
                <div className="actuator-actions">
                  <button type="button" disabled={!isAdmin} onClick={() => handleActuatorCommand('nivus/edge/relay1', 'ON')}>Enviar ON</button>
                  <button type="button" disabled={!isAdmin} onClick={() => handleActuatorCommand('nivus/edge/relay1', 'OFF')}>Enviar OFF</button>
                </div>
              </div>
              <p className="dashboard-status-message" role="status">{actuatorMessage || (isAdmin ? 'Nenhum comando enviado.' : 'Somente administrador pode enviar comandos.')}</p>
              <div className="dashboard-event-list" aria-label="Auditoria recente dos atuadores">
                <strong><History size={14} aria-hidden="true" /> Comandos recentes</strong>
                {auditLogs.length ? auditLogs.slice(0, 5).map((event) => (
                  <div className="dashboard-event-row" key={event.id}>
                    <span>{event.command} · {event.topic}</span>
                    <time>{formatDatabaseTimestamp(event.timestamp)}</time>
                  </div>
                )) : <small>Nenhum comando registrado.</small>}
              </div>
            </section>

            <section className="dashboard-panel dashboard-alert-panel" aria-labelledby="alert-settings-title">
              <div className="dashboard-panel-heading">
                <h3 id="alert-settings-title"><Settings aria-hidden="true" /> Limite de temperatura</h3>
                <div className="dashboard-temperature-sound">
                  <button
                    type="button"
                    className={`temperature-sound-toggle ${soundEnabled ? (isTempCritical ? 'temperature-sound-critical' : 'temperature-sound-enabled') : 'temperature-sound-disabled'}`}
                    aria-pressed={soundEnabled}
                    aria-label={soundEnabled ? 'Desativar aviso sonoro no navegador' : 'Ativar aviso sonoro no navegador'}
                    title={soundEnabled ? 'Desativar aviso sonoro' : 'Ativar aviso sonoro'}
                    onClick={onToggleAlertSound}
                  >
                    {soundEnabled ? <Volume2 size={15} aria-hidden="true" /> : <VolumeX size={15} aria-hidden="true" />}
                  </button>
                  <span>Aviso sonoro</span>
                </div>
              </div>
              <p className="dashboard-panel-copy">Gera alerta quando a leitura de CPU/APU ultrapassa este valor.</p>
              <p className="dashboard-sound-status" role="status" aria-live="polite">
                {soundStatus} O som é reproduzido pelo navegador, não por um buzzer físico.
              </p>
              <div className="threshold-row">
                <label htmlFor="temperature-threshold">Limite (°C)</label>
                <input
                  id="temperature-threshold"
                  type="number"
                  min="0"
                  max="150"
                  step="0.5"
                  disabled={!isAdmin || savingThreshold}
                  value={thresholdDraft}
                  onChange={(event) => {
                    setThresholdDraft(event.target.value);
                    setThresholdDirty(true);
                  }}
                />
                {isAdmin && <button type="button" disabled={savingThreshold || !thresholdDirty || !thresholdValid} onClick={saveThreshold}>{savingThreshold ? 'Salvando…' : 'Salvar'}</button>}
              </div>
              {thresholdDirty && !thresholdValid && <p className="dashboard-input-error" role="alert">Informe um valor entre 0 e 150 °C.</p>}
              <p className={`dashboard-threshold-state ${isTempCritical ? 'dashboard-threshold-high' : ''}`} role={isTempCritical ? 'alert' : 'status'}>
                {isTempCritical
                  ? 'Limite ultrapassado; o worker registra o evento na primeira amostra da subida.'
                  : latest?.temperature_source
                    ? `Leitura atual dentro do limite de ${formatMetric(Number(settings.temp_threshold), '°C')}.`
                    : 'Sem leitura de CPU/APU disponível para avaliar o limite.'}
              </p>
              {settingsStatus && <p className="dashboard-status-message" role="status">{settingsStatus}</p>}
            </section>

            <section className="dashboard-panel dashboard-alert-history-panel" aria-labelledby="alert-history-title">
              <div className="dashboard-panel-heading">
                <h3 id="alert-history-title"><Bell aria-hidden="true" /> Alertas recentes</h3>
                <span className="dashboard-panel-tag">Regra determinística</span>
              </div>
              <p className="dashboard-panel-copy">O worker grava uma ocorrência quando a métrica cruza o limite. Não há notificação remota nesta versão.</p>
              <div className="dashboard-event-list" aria-live="polite">
                {alertsHistory.length ? alertsHistory.slice(0, 5).map((event) => {
                  const alert = alertDescription(event.alert_type);
                  return (
                    <div className="dashboard-event-row" key={event.id}>
                      <span>{alert.name}: {formatMetric(event.value, alert.unit)} · limite {formatMetric(event.threshold, alert.unit)}</span>
                      <time>{formatDatabaseTimestamp(event.timestamp)}</time>
                    </div>
                  );
                }) : <small>Nenhum cruzamento de limite registrado.</small>}
              </div>
            </section>
          </div>

          <section className="dashboard-panel dashboard-logs-panel" aria-labelledby="system-logs-title">
            <div className="dashboard-panel-heading">
              <h3 id="system-logs-title"><Terminal aria-hidden="true" /> Logs do Nivus</h3>
              <span className="dashboard-panel-tag">API + worker MQTT</span>
            </div>
            <p className="dashboard-panel-copy">Eventos da aplicação Nivus. Estes registros não incluem logs do Ubuntu, kernel ou de outros containers.</p>
            <div className="system-log-list" aria-live="polite">
              {systemLogs.length
                ? systemLogs.map((log, index) => <div key={`${index}-${log}`}>{log}</div>)
                : <div className="system-log-empty"><Cpu aria-hidden="true" /> Nenhum registro de aplicação disponível ainda.</div>}
            </div>
          </section>
        </main>
      )}
    </>
  );
}
