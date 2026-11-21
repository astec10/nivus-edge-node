import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  Activity,
  ExternalLink,
  KeyRound,
  PauseCircle,
  PlayCircle,
  RefreshCw,
  Save,
  Send,
  ShieldCheck,
} from 'lucide-react';

const API = '/api/settings/ai-task-controller';
const GITHUB_TOKEN_URL = 'https://github.com/settings/personal-access-tokens/new';

function responseMessage(error, fallback) {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  return detail?.message || fallback;
}

function stateLabel(state) {
  return {
    online: 'Conectado ao GitHub',
    degraded: 'Conexão indisponível',
    disabled: 'Controlador desligado',
    not_configured: 'Configuração incompleta',
    stopped: 'Aguardando inicialização',
    starting: 'Iniciando consulta',
  }[state] || 'Consultando estado';
}

export default function AITaskControllerPanel({ token }) {
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);
  const [config, setConfig] = useState({
    repository: 'astec10/nivus-edge-node',
    poll_interval_seconds: 60,
    max_authorizations_per_day: 3,
    enabled: false,
    credential_configured: false,
    last_test_status: 'not_tested',
  });
  const [status, setStatus] = useState({ state: 'stopped', tasks: [] });
  const [form, setForm] = useState({
    repository: config.repository,
    poll_interval_seconds: '60',
    max_authorizations_per_day: '3',
  });
  const [formDirty, setFormDirty] = useState(false);
  const [githubToken, setGithubToken] = useState('');
  const [audit, setAudit] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  const refresh = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const [controllerResponse, auditResponse] = await Promise.all([
        axios.get(API, { headers }),
        axios.get(`${API}/audit?limit=20`, { headers }),
      ]);
      const nextConfig = controllerResponse.data.config;
      setConfig(nextConfig);
      setStatus(controllerResponse.data.status || { state: 'stopped', tasks: [] });
      if (!formDirty) {
        setForm({
          repository: nextConfig.repository,
          poll_interval_seconds: String(nextConfig.poll_interval_seconds),
          max_authorizations_per_day: String(nextConfig.max_authorizations_per_day),
        });
      }
      setAudit(Array.isArray(auditResponse.data) ? auditResponse.data : []);
    } catch (error) {
      setMessage(responseMessage(error, 'Não foi possível consultar o controlador GitHub.'));
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [formDirty, headers]);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => void refresh(true), 30000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  const saveSettings = async () => {
    setBusy(true);
    setMessage('Salvando configuração…');
    try {
      const payload = {
        repository: form.repository.trim(),
        poll_interval_seconds: Number(form.poll_interval_seconds),
        max_authorizations_per_day: Number(form.max_authorizations_per_day),
        ...(githubToken.trim() ? { github_token: githubToken.trim() } : {}),
      };
      const response = await axios.put(API, payload, { headers });
      setConfig(response.data);
      setFormDirty(false);
      setGithubToken('');
      setMessage('Configuração salva. O token fica cifrado e nunca é mostrado novamente.');
      await refresh(true);
      return true;
    } catch (error) {
      setMessage(responseMessage(error, 'Não foi possível salvar a configuração.'));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const submitSettings = async event => {
    event.preventDefault();
    await saveSettings();
  };

  const testConnection = async () => {
    const saved = await saveSettings();
    if (!saved) return;
    setBusy(true);
    setMessage('Testando acesso de leitura ao GitHub, sem alterar Issues…');
    try {
      const response = await axios.post(`${API}/connection-test`, null, { headers });
      setMessage(response.data.message || 'Conexão confirmada.');
      await refresh(true);
    } catch (error) {
      setMessage(responseMessage(error, 'Não foi possível validar o token.'));
      await refresh(true);
    } finally {
      setBusy(false);
    }
  };

  const refreshQueue = async () => {
    setBusy(true);
    setMessage('Consultando a fila do GitHub…');
    try {
      await axios.post(`${API}/refresh`, null, { headers });
      await refresh(true);
    } catch (error) {
      setMessage(responseMessage(error, 'Não foi possível consultar a fila.'));
      await refresh(true);
    } finally {
      setBusy(false);
    }
  };

  const toggleController = async () => {
    const next = !config.enabled;
    if (next && !window.confirm('Habilitar a consulta contínua da fila? Isso não autoriza chamadas de modelo: cada Issue ainda exige confirmação individual e respeita o limite diário configurado.')) return;
    setBusy(true);
    try {
      const response = await axios.put(`${API}/enabled`, { enabled: next }, { headers });
      setConfig(response.data);
      setMessage(next
        ? 'Controlador habilitado. A fila continua no GitHub e será consultada pelo notebook.'
        : 'Controlador desligado. Issues e histórico continuam preservados no GitHub.');
      await refresh(true);
    } catch (error) {
      setMessage(responseMessage(error, 'Não foi possível alterar o controlador.'));
    } finally {
      setBusy(false);
    }
  };

  const authorizeTask = async task => {
    const accepted = window.confirm(
      `Issue #${task.number}: confirme que revisou o conteúdo público/sintético e autoriza UMA chamada de modelo free-tier. O GitHub Actions iniciará o worker após a label ai:ready. A modalidade free-tier não limita cobrança se o projeto do provedor tiver faturamento habilitado. O notebook não enviará o prompt nem executará o código. Continuar?`
    );
    if (!accepted) return;
    setBusy(true);
    setMessage(`Solicitando autorização da Issue #${task.number}…`);
    try {
      const response = await axios.post(`${API}/issues/${task.number}/authorize`, {
        confirm_free_tier_call: true,
      }, { headers });
      setMessage(response.data.message || 'Issue autorizada.');
      await refresh(true);
    } catch (error) {
      setMessage(responseMessage(error, 'Não foi possível autorizar a Issue. Atualize a fila antes de repetir.'));
      await refresh(true);
    } finally {
      setBusy(false);
    }
  };

  const tasks = Array.isArray(status.tasks) ? status.tasks : [];

  return (
    <section className="settings-card ai-task-controller" aria-labelledby="ai-task-controller-title">
      <div className="settings-card-heading">
        <div>
          <h3 id="ai-task-controller-title">Controlador de tarefas GitHub</h3>
          <p>O notebook acompanha e autoriza a fila. GitHub Actions executa cada proposta em um runner hospedado descartável.</p>
        </div>
        <span className={`maintenance-status time-sync-status--${status.state || 'unknown'}`} role="status">
          <Activity size={14} aria-hidden="true" /> {stateLabel(status.state)}
        </span>
      </div>

      <div className="provider-security-note">
        <ShieldCheck size={17} aria-hidden="true" />
        <p>
          Nenhum código de Issue é executado no notebook. O token é cifrado com a chave mestra local.
          Cada chamada de modelo precisa de confirmação individual; falhas de rede nunca repetem uma autorização automaticamente.
          A API precisa de saída HTTPS/DNS; este painel não abre portas públicas nem configura a ONU.
        </p>
      </div>

      <form className="provider-form" onSubmit={submitSettings}>
        <h4>Conexão e consulta</h4>
        <div className="provider-fields-grid">
          <label className="display-preference-field">
            <span>Repositório GitHub</span>
            <input
              value={form.repository}
              onChange={event => {
                setForm(current => ({ ...current, repository: event.target.value }));
                setFormDirty(true);
              }}
              autoComplete="off"
              maxLength={141}
              required
              aria-label="Repositório no formato proprietário/nome"
            />
          </label>
          <label className="display-preference-field">
            <span>Intervalo de consulta (segundos)</span>
            <input
              type="number"
              min="30"
              max="900"
              step="1"
              value={form.poll_interval_seconds}
              onChange={event => {
                setForm(current => ({ ...current, poll_interval_seconds: event.target.value }));
                setFormDirty(true);
              }}
              required
            />
          </label>
          <label className="display-preference-field">
            <span>Máximo de autorizações por 24 horas</span>
            <input
              type="number"
              min="1"
              max="10"
              step="1"
              value={form.max_authorizations_per_day}
              onChange={event => {
                setForm(current => ({ ...current, max_authorizations_per_day: event.target.value }));
                setFormDirty(true);
              }}
              required
            />
          </label>
          <label className="display-preference-field ai-controller-token-field">
            <span>Token fine-grained do GitHub</span>
            <input
              type="password"
              value={githubToken}
              onChange={event => setGithubToken(event.target.value)}
              placeholder={config.credential_configured ? 'Token salvo; deixe vazio para manter' : 'Cole o token aqui'}
              autoComplete="new-password"
              maxLength={255}
              aria-describedby="ai-controller-token-help"
            />
          </label>
        </div>
        <p className="provider-inline-note" id="ai-controller-token-help">
          Crie um token para este repositório com <strong>Issues: Read and write</strong> e Metadata read. Não conceda Contents nem Actions write.
          <a href={GITHUB_TOKEN_URL} target="_blank" rel="noreferrer"> Criar token fine-grained <ExternalLink size={13} aria-hidden="true" /></a>
        </p>
        <div className="time-sync-actions ai-controller-actions">
          <button type="submit" disabled={busy || loading}>
            <Save size={16} aria-hidden="true" /> Salvar configuração
          </button>
          <button type="button" className="time-sync-rollback" onClick={() => void testConnection()} disabled={busy || loading}>
            <KeyRound size={16} aria-hidden="true" /> Testar conexão
          </button>
          <button type="button" className="time-sync-rollback" onClick={() => void toggleController()} disabled={busy || loading}>
            {config.enabled ? <PauseCircle size={16} aria-hidden="true" /> : <PlayCircle size={16} aria-hidden="true" />}
            {config.enabled ? 'Desligar controlador' : 'Habilitar controlador'}
          </button>
          <button type="button" className="time-sync-rollback" onClick={() => void refreshQueue()} disabled={busy || loading || !config.enabled}>
            <RefreshCw size={16} aria-hidden="true" /> Atualizar fila
          </button>
        </div>
        <p className="maintenance-message" role="status" aria-live="polite">
          {message || (config.credential_configured
            ? `Token salvo. Último teste: ${config.last_test_status || 'ainda não testado'}.`
            : 'Cadastre e teste o token antes de habilitar o controlador.')}
        </p>
      </form>

      <div className="ai-task-queue" aria-labelledby="ai-task-queue-title">
        <div className="provider-entry-heading">
          <div>
            <h4 id="ai-task-queue-title">Fila de Issues</h4>
            <p>Última consulta: {status.last_poll_at ? new Date(status.last_poll_at).toLocaleString() : 'ainda não consultada'}</p>
          </div>
          <span className="maintenance-status">{tasks.length} tarefa(s)</span>
        </div>
        {status.last_error_code && (
          <p className="maintenance-message ai-controller-warning" role="status">
            A última consulta falhou ({status.last_error_code}). Os itens exibidos podem estar desatualizados e a autorização fica bloqueada até uma consulta bem-sucedida. A fila permanece no GitHub; o controlador tentará novamente no próximo intervalo.
          </p>
        )}
        {tasks.length === 0 ? (
          <p className="provider-inline-note">{!config.enabled ? 'Habilite o controlador para acompanhar as Issues da fila.' : status.state === 'online' ? 'Nenhuma Issue ai:queued ou ai:ready encontrada.' : 'Aguardando uma consulta bem-sucedida ao GitHub.'}</p>
        ) : (
          <ul className="ai-task-list">
            {tasks.map(task => (
              <li key={task.number} className="ai-task-entry">
                <div className="ai-task-summary">
                  <a href={task.url} target="_blank" rel="noreferrer">
                    <strong>#{task.number}</strong> {task.title} <ExternalLink size={13} aria-hidden="true" />
                  </a>
                  <span className={`maintenance-status ${task.queue_state === 'authorized' ? 'time-sync-status--synchronized' : ''}`}>
                    {task.queue_state === 'authorized' ? 'Autorizada' : task.can_authorize ? 'Pronta para revisão' : 'Contrato inválido'}
                  </span>
                </div>
                {task.queue_state === 'authorized' ? (
                  <p className="provider-inline-note">A label ai:ready foi aplicada. Acompanhe a execução e eventuais PRs no GitHub.</p>
                ) : task.can_authorize ? (
                  <button type="button" className="ai-task-authorize" onClick={() => void authorizeTask(task)} disabled={busy || !config.enabled || status.state !== 'online'}>
                    <Send size={15} aria-hidden="true" /> Revisar e autorizar uma chamada
                  </button>
                ) : (
                  <p className="provider-inline-note">Abra a Issue para corrigir o formulário, a classificação ou o orçamento antes de autorizar.</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <details className="provider-audit">
        <summary>Histórico local de configuração e autorizações</summary>
        <ul>
          {audit.length === 0
            ? <li>Nenhum evento local registrado.</li>
            : audit.map((entry, index) => (
              <li key={`${entry.created_at}-${index}`}>
                {new Date(entry.created_at * 1000).toLocaleString()} · {entry.action} · Issue {entry.issue_number ? `#${entry.issue_number}` : '—'} · {entry.outcome}
              </li>
            ))}
        </ul>
      </details>
    </section>
  );
}
