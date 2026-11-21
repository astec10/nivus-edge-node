import React, { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import {
  Activity,
  AlertTriangle,
  CircleAlert,
  RefreshCw,
} from 'lucide-react';
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
import { formatDisplayDate } from '../utils/displayPreferences';
import './NodeTelemetryHistory.css';

const QUERY_LIMIT = 500;
const STALE_AFTER_SECONDS = 90;
const CLOCK_SKEW_WARNING_SECONDS = 60;

const RANGES = [
  { key: '5m', label: '5 min', milliseconds: 5 * 60 * 1000 },
  { key: '15m', label: '15 min', milliseconds: 15 * 60 * 1000 },
  { key: '30m', label: '30 min', milliseconds: 30 * 60 * 1000 },
  { key: '1h', label: '1 hora', milliseconds: 60 * 60 * 1000 },
  { key: '6h', label: '6 horas', milliseconds: 6 * 60 * 60 * 1000 },
  { key: '24h', label: '24 horas', milliseconds: 24 * 60 * 60 * 1000 },
  { key: '14d', label: '14 dias', milliseconds: 14 * 24 * 60 * 60 * 1000 },
];

const SERIES = [
  { metric: 'cpu.utilization', key: 'cpuPercent', label: 'CPU', unit: '%', color: '#38bdf8' },
  { metric: 'memory.utilization', key: 'memoryPercent', label: 'Memória', unit: '%', color: '#a78bfa' },
  { metric: 'disk.utilization', key: 'diskPercent', label: 'Disco', unit: '%', color: '#34d399' },
];

const QUALITY_LABELS = {
  measured: 'Medido',
  estimated: 'Estimado',
  unavailable: 'Indisponível',
};

function formatValue(value, unit) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 'N/D';
  const formatted = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(value);
  return unit === '%' ? formatted + '%' : formatted + ' ' + unit;
}

function formatTimestamp(value, preferences = {}) {
  if (!value) return 'Horário indisponível';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Horário inválido';
  const timeZone = preferences.timeZone || 'America/Sao_Paulo';
  const dateText = formatDisplayDate(date, timeZone, preferences.dateFormat);
  const timeText = new Intl.DateTimeFormat('pt-BR', {
    timeZone,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    ...(preferences.timeFormat === '12h' ? { hour12: true } : { hourCycle: 'h23' }),
  }).format(date);
  return dateText + ' ' + timeText;
}

function formatClockTime(value, timeZone) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('pt-BR', {
    timeZone: timeZone || 'America/Sao_Paulo',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
}

function normalizeBatches(batches) {
  if (!Array.isArray(batches)) return [];
  return batches.map((batch) => {
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
    SERIES.forEach((series) => {
      const sample = samples.find((item) => item && item.metric === series.metric);
      const numericValue = sample && typeof sample.value === 'number'
        && Number.isFinite(sample.value)
        ? sample.value
        : null;
      row[series.key] = sample && sample.quality !== 'unavailable' ? numericValue : null;
      row[series.key + 'Quality'] = sample && QUALITY_LABELS[sample.quality]
        ? sample.quality
        : 'unavailable';
    });
    return row;
  }).filter(Boolean);
}

function HistoryTooltip({ active, payload, visibleSeries, displayPreferences }) {
  const row = payload && payload.length ? payload[0].payload : null;
  if (!active || !row) return null;
  return (
    <div className="node-history-tooltip">
      <strong>Recebido: {formatTimestamp(row.receivedAt, displayPreferences)}</strong>
      <small>Informado pelo nó: {formatTimestamp(row.observedAt, displayPreferences)}</small>
      {visibleSeries.map((series) => (
        <div className="node-history-tooltip__metric" key={series.key}>
          <span style={{ color: series.color }}>{series.label}</span>
          <strong>{formatValue(row[series.key], series.unit)}</strong>
          <small>{QUALITY_LABELS[row[series.key + 'Quality']] || 'Indisponível'}</small>
        </div>
      ))}
      {row.clockSkewSeconds !== null && Math.abs(row.clockSkewSeconds) > CLOCK_SKEW_WARNING_SECONDS && (
        <small className="node-history-tooltip__warning">
          Diferença observada de horário: {new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 }).format(row.clockSkewSeconds)} s.
          O atraso de rede também influencia esta diferença.
        </small>
      )}
    </div>
  );
}

function summarize(rows, key) {
  const values = rows.map((row) => row[key]).filter((value) => typeof value === 'number' && Number.isFinite(value));
  if (!values.length) return { minimum: null, maximum: null, latest: null };
  return {
    minimum: Math.min(...values),
    maximum: Math.max(...values),
    latest: values[values.length - 1],
  };
}

export default function NodeTelemetryHistory({
  node,
  token,
  displayPreferences,
  serverNowMs,
}) {
  const [range, setRange] = useState('15m');
  const [chartType, setChartType] = useState('line');
  const [visibleKeys, setVisibleKeys] = useState(() => new Set(SERIES.map((item) => item.key)));
  const [reload, setReload] = useState(0);
  const [showDetails, setShowDetails] = useState(false);
  const [result, setResult] = useState({ key: '', batches: [] });
  const [loadingKey, setLoadingKey] = useState('');
  const [error, setError] = useState({ key: '', message: '' });
  const [loadedAt, setLoadedAt] = useState(null);
  const activeRequest = useRef(null);

  const queryKey = node.node_id + ':' + range + ':' + reload;

  useEffect(() => {
    activeRequest.current && activeRequest.current.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setLoadingKey(queryKey);
    setError({ key: queryKey, message: '' });

    const selectedRange = RANGES.find((item) => item.key === range);
    const referenceNow = Number.isFinite(serverNowMs) ? serverNowMs : Date.now();
    const params = { limit: QUERY_LIMIT };
    if (selectedRange) {
      params.since = new Date(referenceNow - selectedRange.milliseconds).toISOString();
    }

    axios.get('/api/nodes/' + encodeURIComponent(node.node_id) + '/telemetry', {
      params,
      headers: { Authorization: 'Bearer ' + token },
      signal: controller.signal,
    }).then((response) => {
      if (!controller.signal.aborted && activeRequest.current === controller) {
        setResult({
          key: queryKey,
          batches: Array.isArray(response.data) ? response.data : [],
        });
        setLoadedAt(new Date());
      }
    }).catch((requestError) => {
      if (requestError.code === 'ERR_CANCELED' || controller.signal.aborted) return;
      const statusCode = requestError.response && requestError.response.status;
      const message = statusCode === 401
        ? 'Sessão expirada. Entre novamente para consultar o histórico.'
        : statusCode === 403
          ? 'Sua conta não tem permissão de administrador para consultar este histórico.'
          : statusCode === 404
            ? 'O endpoint ou o nó não foi encontrado. Confirme se as releases do registro e do histórico foram integradas.'
            : statusCode === 422
              ? 'O período ou identificador foi rejeitado pela API.'
              : 'Falha de rede ao consultar o histórico. Tente atualizar novamente.';
      if (activeRequest.current === controller) {
        setError({ key: queryKey, message });
      }
    }).finally(() => {
      if (activeRequest.current === controller) {
        activeRequest.current = null;
        setLoadingKey('');
      }
    });

    return () => {
      controller.abort();
      if (activeRequest.current === controller) activeRequest.current = null;
    };
  }, [node.node_id, token, range, reload, queryKey, serverNowMs]);

  const batches = result.key === queryKey ? result.batches : [];
  const requestError = error.key === queryKey ? error.message : '';
  const isLoading = loadingKey === queryKey;
  const rows = useMemo(() => normalizeBatches(batches), [batches]);
  const visibleSeries = SERIES.filter((item) => visibleKeys.has(item.key));
  const summaries = useMemo(
    () => Object.fromEntries(SERIES.map((item) => [item.key, summarize(rows, item.key)])),
    [rows],
  );
  const hasVisibleValues = visibleSeries.some((item) => summaries[item.key].latest !== null);
  const latest = rows.length ? rows[rows.length - 1] : null;
  const latestAgeSeconds = latest && Number.isFinite(serverNowMs)
    ? (serverNowMs - latest.receivedMs) / 1000
    : latest ? (Date.now() - latest.receivedMs) / 1000 : null;
  const stale = Number.isFinite(latestAgeSeconds) && latestAgeSeconds > STALE_AFTER_SECONDS;
  const hasClockSkew = rows.some((row) => row.clockSkewSeconds !== null
    && Math.abs(row.clockSkewSeconds) > CLOCK_SKEW_WARNING_SECONDS);
  const ChartComponent = chartType === 'area' ? AreaChart : chartType === 'bar' ? BarChart : LineChart;
  const nodeStatus = node.status || 'offline';

  function toggleSeries(key) {
    setVisibleKeys((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function toggleAllSeries() {
    const allVisible = visibleKeys.size === SERIES.length;
    setVisibleKeys(allVisible ? new Set() : new Set(SERIES.map((item) => item.key)));
  }

  return (
    <section className="node-telemetry-history" aria-labelledby="node-history-title">
      <div className="node-telemetry-history__heading">
        <div>
          <h4 id="node-history-title"><Activity aria-hidden="true" size={17} /> Histórico de telemetria</h4>
          <p>Dados enviados pelo agente e recebidos pelo Nó Master. Somente leitura; nenhum comando é enviado ao nó.</p>
        </div>
        <button
          className="node-history-refresh"
          type="button"
          onClick={() => setReload((value) => value + 1)}
          disabled={isLoading}
        >
          <RefreshCw size={14} aria-hidden="true" className={isLoading ? 'is-spinning' : ''} />
          Atualizar histórico
        </button>
      </div>

      {nodeStatus === 'offline' && (
        <p className="node-history-banner node-history-banner--offline" role="status">
          <CircleAlert size={16} aria-hidden="true" /> Nó offline; exibindo o histórico já recebido, se houver.
        </p>
      )}
      {nodeStatus === 'revoked' && (
        <p className="node-history-banner node-history-banner--revoked" role="status">
          <CircleAlert size={16} aria-hidden="true" /> Nó revogado; os dados históricos permanecem somente para consulta administrativa.
        </p>
      )}
      {stale && (
        <p className="node-history-banner node-history-banner--stale" role="status">
          <AlertTriangle size={16} aria-hidden="true" /> A última amostra recebida tem mais de 90 segundos.
        </p>
      )}
      {hasClockSkew && (
        <p className="node-history-banner node-history-banner--clock" role="note">
          <AlertTriangle size={16} aria-hidden="true" /> Há diferença superior a 60 segundos entre o horário informado pelo nó e o recebimento no Master. O atraso de rede também influencia essa diferença.
        </p>
      )}

      <div className="node-history-controls">
        <div className="node-history-control-group" role="group" aria-label="Período do histórico">
          <span>Período</span>
          <div className="node-history-button-row">
            {RANGES.map((item) => (
              <button
                type="button"
                key={item.key}
                aria-pressed={range === item.key}
                className="node-history-choice"
                onClick={() => setRange(item.key)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <div className="node-history-control-group" role="group" aria-label="Séries visíveis">
          <span>Séries</span>
          <div className="node-history-button-row">
            {SERIES.map((item) => (
              <button
                type="button"
                key={item.key}
                aria-pressed={visibleKeys.has(item.key)}
                className="node-history-choice node-history-series-choice"
                onClick={() => toggleSeries(item.key)}
              >
                <span className="node-history-series-dot" style={{ backgroundColor: item.color }} aria-hidden="true" />
                {item.label}
              </button>
            ))}
            <button
              type="button"
              className="node-history-choice"
              aria-pressed={visibleKeys.size === SERIES.length}
              onClick={toggleAllSeries}
            >
              {visibleKeys.size === SERIES.length ? 'Ocultar todas' : 'Mostrar todas'}
            </button>
          </div>
        </div>

        <label className="node-history-control-group node-history-chart-type">
          <span>Tipo de gráfico</span>
          <select value={chartType} onChange={(event) => setChartType(event.target.value)}>
            <option value="line">Linha</option>
            <option value="area">Área</option>
            <option value="bar">Barras</option>
          </select>
        </label>
      </div>

      <div className="node-history-summary" aria-label="Resumo das métricas visíveis">
        {visibleSeries.map((item) => (
          <div key={item.key} className="node-history-summary__item">
            <span><i style={{ backgroundColor: item.color }} aria-hidden="true" />{item.label}</span>
            <strong>{formatValue(summaries[item.key].latest, item.unit)}</strong>
            <small>
              Mín {formatValue(summaries[item.key].minimum, item.unit)} · Máx {formatValue(summaries[item.key].maximum, item.unit)}
            </small>
          </div>
        ))}
      </div>

      {requestError && <p className="node-history-error" role="alert">{requestError}</p>}
      {isLoading && rows.length === 0 && !requestError && (
        <div className="node-history-empty" role="status">Consultando histórico do nó…</div>
      )}
      {!isLoading && !requestError && batches.length === 0 && (
        <div className="node-history-empty" role="status">
          Nenhuma amostra no período selecionado. A API mantém até 14 dias e 500 lotes por consulta.
        </div>
      )}
      {!requestError && rows.length > 0 && !hasVisibleValues && visibleSeries.length > 0 && (
        <div className="node-history-empty" role="status">
          Não há valores numéricos disponíveis para as séries selecionadas neste período. Leituras indisponíveis aparecem como N/D.
        </div>
      )}
      {!requestError && visibleSeries.length === 0 && (
        <div className="node-history-empty" role="status">Selecione ao menos uma série para exibir o gráfico.</div>
      )}
      {!requestError && rows.length > 0 && hasVisibleValues && visibleSeries.length > 0 && (
        <figure className="node-history-figure" aria-labelledby="node-history-chart-caption">
          <figcaption id="node-history-chart-caption">Uso de CPU, memória e disco — eixo horizontal: horário de recebimento no Master</figcaption>
          <div className="node-history-chart">
            <ResponsiveContainer width="100%" height="100%">
              <ChartComponent data={rows} margin={{ top: 8, right: 14, bottom: 4, left: 0 }} accessibilityLayer>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--node-history-grid, #334155)" />
                <XAxis
                  dataKey="receivedMs"
                  type="number"
                  domain={['dataMin', 'dataMax']}
                  tickFormatter={(value) => formatClockTime(value, displayPreferences && displayPreferences.timeZone)}
                  tick={{ fill: 'var(--node-history-muted, #94a3b8)', fontSize: 11 }}
                  minTickGap={28}
                />
                <YAxis
                  domain={[0, 100]}
                  unit="%"
                  width={44}
                  tick={{ fill: 'var(--node-history-muted, #94a3b8)', fontSize: 11 }}
                />
                <Tooltip
                  content={(props) => (
                    <HistoryTooltip
                      {...props}
                      visibleSeries={visibleSeries}
                      displayPreferences={displayPreferences}
                    />
                  )}
                />
                {visibleSeries.map((item) => {
                  const commonProps = {
                    key: item.key,
                    dataKey: item.key,
                    name: item.label,
                    stroke: item.color,
                    fill: item.color,
                    strokeWidth: 2,
                    isAnimationActive: false,
                    connectNulls: false,
                  };
                  if (chartType === 'area') {
                    return <Area {...commonProps} type="monotone" fillOpacity={0.12} dot={false} />;
                  }
                  if (chartType === 'bar') return <Bar {...commonProps} />;
                  return <Line {...commonProps} type="monotone" dot={false} />;
                })}
              </ChartComponent>
            </ResponsiveContainer>
          </div>
        </figure>
      )}

      <div className="node-history-footer">
        <span>
          {batches.length} lotes exibidos; máximo {QUERY_LIMIT}. {Number.isFinite(serverNowMs) ? 'Período calculado pelo horário estimado do Master.' : 'Período calculado pelo relógio deste navegador.'}
        </span>
        {loadedAt && result.key === queryKey && (
          <span aria-live="polite">Atualizado às {formatTimestamp(loadedAt.toISOString(), displayPreferences)}</span>
        )}
      </div>

      <button
        className="node-history-details-toggle"
        type="button"
        aria-expanded={showDetails}
        aria-controls="node-history-details"
        onClick={() => setShowDetails((value) => !value)}
      >
        {showDetails ? 'Ocultar informações detalhadas' : 'Mostrar todas as informações'}
      </button>
      {showDetails && (
        <div id="node-history-details" className="node-history-table-wrap">
          <table className="node-history-table">
            <caption>Até 500 lotes mais recentes dentro do período e da retenção de 14 dias</caption>
            <thead>
              <tr>
                <th scope="col">Recebido no Master</th>
                <th scope="col">Informado pelo nó</th>
                {SERIES.map((item) => <th scope="col" key={item.key}>{item.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.slice().reverse().map((row, index) => (
                <tr key={row.receivedAt + ':' + index}>
                  <td>{formatTimestamp(row.receivedAt, displayPreferences)}</td>
                  <td>{formatTimestamp(row.observedAt, displayPreferences)}</td>
                  {SERIES.map((item) => (
                    <td key={item.key}>
                      {formatValue(row[item.key], item.unit)}
                      <small>{QUALITY_LABELS[row[item.key + 'Quality']] || 'Indisponível'}</small>
                    </td>
                  ))}
                </tr>
              ))}
              {!rows.length && (
                <tr><td colSpan={SERIES.length + 2}>Nenhum lote disponível para detalhar.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
