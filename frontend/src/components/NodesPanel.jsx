import React, { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Activity, CircleAlert, CircleCheck, CircleX, Network, RefreshCw } from 'lucide-react';
import { DEFAULT_DISPLAY_PREFERENCES, formatDisplayDate } from '../utils/displayPreferences';
import './NodesPanel.css';

const REFRESH_INTERVAL_MS = 30_000;

const NODE_STATUS = {
  online: { label: 'Online', Icon: CircleCheck },
  offline: { label: 'Offline', Icon: CircleX },
  revoked: { label: 'Revogado', Icon: CircleAlert },
};

function formatAge(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return 'Nunca recebeu heartbeat';
  if (seconds < 60) return `há ${seconds} s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `há ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `há ${hours} h`;
  return `há ${Math.floor(hours / 24)} d`;
}

function formatTimestamp(value, preferences) {
  if (!value) return 'Sem registro';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Horário inválido';
  const time = new Intl.DateTimeFormat('pt-BR', {
    timeZone: preferences.timeZone,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    ...(preferences.timeFormat === '12h' ? { hour12: true } : { hourCycle: 'h23' }),
  }).format(date);
  return `${formatDisplayDate(date, preferences.timeZone, preferences.dateFormat)} ${time}`;
}

function NodeCard({ node, preferences }) {
  const statusKey = NODE_STATUS[node.status] ? node.status : 'offline';
  const status = NODE_STATUS[statusKey];
  const StatusIcon = status.Icon;
  const capabilities = Array.isArray(node.capabilities) ? node.capabilities : [];

  return (
    <article className="node-registry-card" aria-labelledby={`node-name-${node.node_id}`}>
      <div className="node-registry-card__heading">
        <div className="node-registry-card__title">
          <h3 id={`node-name-${node.node_id}`}>{node.name || 'Nó sem nome'}</h3>
          <code title={node.node_id}>{node.node_id}</code>
        </div>
        <span className={`node-registry-status node-registry-status--${statusKey}`}>
          <StatusIcon size={15} aria-hidden="true" /> {status.label}
        </span>
      </div>

      <dl className="node-registry-details">
        <div>
          <dt>Último heartbeat</dt>
          <dd title={node.last_seen ? formatTimestamp(node.last_seen, preferences) : undefined}>
            {formatAge(node.last_seen_seconds_ago)}
          </dd>
        </div>
        <div>
          <dt>Agente</dt>
          <dd>{node.agent_version || 'Não informado'}</dd>
        </div>
        <div>
          <dt>Schema</dt>
          <dd>{Number.isInteger(node.schema_version) ? `v${node.schema_version}` : 'Não informado'}</dd>
        </div>
      </dl>

      <div className="node-registry-capabilities">
        <strong>Capacidades declaradas</strong>
        {capabilities.length ? (
          <ul>
            {capabilities.map(capability => <li key={capability}><code>{capability}</code></li>)}
          </ul>
        ) : <p>Nenhuma capacidade declarada.</p>}
        <small>Informação declarada pelo agente; não comprova leitura ou disponibilidade do recurso.</small>
      </div>
    </article>
  );
}

export default function NodesPanel({ token, displayPreferences = DEFAULT_DISPLAY_PREFERENCES }) {
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState(null);
  const requestController = useRef(null);

  const refreshNodes = useCallback(async (isInitial = false) => {
    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    if (isInitial) setLoading(true);
    else setRefreshing(true);
    try {
      const response = await axios.get('/api/nodes', {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      });
      setNodes(Array.isArray(response.data) ? response.data : []);
      setError('');
      setLastRefresh(new Date());
    } catch (requestError) {
      if (requestError.code !== 'ERR_CANCELED' && requestController.current === controller) {
        const statusCode = requestError.response?.status;
        setError(statusCode === 401 || statusCode === 403
          ? 'A sessão expirou ou não tem permissão de administrador para consultar os nós.'
          : 'Não foi possível consultar o registro de nós. Tente novamente.');
      }
    } finally {
      if (requestController.current === controller) {
        requestController.current = null;
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [token]);

  useEffect(() => {
    void refreshNodes(true);
    const timer = window.setInterval(() => void refreshNodes(), REFRESH_INTERVAL_MS);
    return () => {
      window.clearInterval(timer);
      requestController.current?.abort();
      requestController.current = null;
    };
  }, [refreshNodes]);

  const handleRefresh = () => void refreshNodes();

  return (
    <section className="dashboard-panel node-registry-panel" aria-labelledby="node-registry-title">
      <div className="dashboard-panel-heading">
        <h3 id="node-registry-title"><Network aria-hidden="true" /> Registro de nós</h3>
        <button className="node-registry-refresh" type="button" onClick={handleRefresh} disabled={refreshing || loading}>
          <RefreshCw size={15} aria-hidden="true" className={refreshing ? 'is-spinning' : ''} />
          Atualizar
        </button>
      </div>

      <p className="dashboard-panel-copy">
        Presença e último heartbeat informados pelo servidor. A lista atualiza automaticamente a cada 30 segundos.
      </p>

      <div className="node-registry-telemetry-note" role="note">
        <Activity size={17} aria-hidden="true" />
        <p>As séries de telemetria ainda não são recebidas nem agregadas por nó nesta etapa.</p>
      </div>

      {lastRefresh && (
        <p className="node-registry-updated" aria-live="polite">
          Consulta concluída às {formatTimestamp(lastRefresh.toISOString(), displayPreferences)}
        </p>
      )}

      {error && <p className="node-registry-error" role="alert">{error}</p>}
      {loading ? (
        <div className="node-registry-empty" role="status">Consultando nós…</div>
      ) : error && nodes.length === 0 ? (
        <div className="node-registry-empty">Lista de nós indisponível. Use Atualizar para tentar novamente.</div>
      ) : nodes.length === 0 ? (
        <div className="node-registry-empty">Nenhum nó registrado ainda.</div>
      ) : (
        <div className="node-registry-grid">
          {nodes.map(node => <NodeCard key={node.node_id} node={node} preferences={displayPreferences} />)}
        </div>
      )}
    </section>
  );
}
