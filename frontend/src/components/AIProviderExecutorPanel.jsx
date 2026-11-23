import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { Play, ShieldCheck } from 'lucide-react';
import './AIProviderExecutorPanel.css';

const PROVIDERS_API = '/api/settings/ai-providers';
const EXECUTOR_API = '/api/ai/executor';
const DATA_CLASSES = [
  { id: 'public', label: 'Públicos' },
  { id: 'synthetic', label: 'Sintéticos' },
  { id: 'operational', label: 'Operação' },
  { id: 'personal', label: 'Pessoais' },
  { id: 'home', label: 'Residenciais' },
  { id: 'camera', label: 'Câmeras' },
];

function newTaskId() {
  const id = globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2);
  return 'nivus-' + id;
}

export default function AIProviderExecutorPanel({ token }) {
  const headers = useMemo(() => ({ Authorization: 'Bearer ' + token }), [token]);
  const [providers, setProviders] = useState([]);
  const [mode, setMode] = useState('single');
  const [providerId, setProviderId] = useState('');
  const [providerIds, setProviderIds] = useState([]);
  const [prompt, setPrompt] = useState('');
  const [dataClass, setDataClass] = useState('synthetic');
  const [taskBudget, setTaskBudget] = useState('0.01');
  const [taskId, setTaskId] = useState(newTaskId);
  const [maxOutputTokens, setMaxOutputTokens] = useState('1024');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [result, setResult] = useState(null);

  useEffect(() => {
    let active = true;
    axios.get(PROVIDERS_API, { headers })
      .then(response => {
        if (!active) return;
        const ready = Array.isArray(response.data)
          ? response.data.filter(item => item.enabled && item.last_test_status === 'success')
          : [];
        setProviders(ready);
        setProviderId(current => current || ready[0]?.id || '');
        setProviderIds(current => current.length ? current : ready.slice(0, 2).map(item => item.id));
      })
      .catch(error => {
        if (active) setMessage(error.response?.data?.detail || 'Não foi possível carregar provedores prontos.');
      });
    return () => { active = false; };
  }, [headers]);

  const eligibleProviders = providers.filter(provider =>
    provider.allowed_data_classes?.includes(dataClass)
    && (provider.endpoint_scope !== 'cloud' || ['public', 'synthetic'].includes(dataClass))
  );

  useEffect(() => {
    const eligibleProvidersForClass = providers.filter(provider =>
      provider.allowed_data_classes?.includes(dataClass)
      && (provider.endpoint_scope !== 'cloud' || ['public', 'synthetic'].includes(dataClass))
    );
    const eligibleIds = new Set(eligibleProvidersForClass.map(item => item.id));
    setProviderIds(current => {
      const next = current.filter(id => eligibleIds.has(id));
      return next.length === current.length ? current : next;
    });
    setProviderId(current => eligibleIds.has(current) ? current : eligibleProvidersForClass[0]?.id || '');
  }, [dataClass, providers]);

  const toggleProvider = id => {
    setProviderIds(current => current.includes(id)
      ? current.filter(item => item !== id)
      : current.length < 3 ? [...current, id] : current);
  };

  const execute = async event => {
    event.preventDefault();
    if (!prompt.trim()) {
      setMessage('Descreva a tarefa antes de executar.');
      return;
    }
    const selected = mode === 'single' ? [providerId] : providerIds;
    if (selected.some(id => !id) || (mode === 'parallel' && (selected.length < 2 || selected.length > 3))) {
      setMessage(mode === 'parallel'
        ? 'Selecione de dois a três provedores elegíveis.'
        : 'Selecione um provedor pronto.');
      return;
    }
    setBusy(true);
    setMessage(mode === 'parallel' ? 'Executando chamadas em paralelo…' : 'Executando uma chamada…');
    setResult(null);
    const common = {
      request_id: globalThis.crypto?.randomUUID?.() || newTaskId(),
      task_id: taskId,
      prompt,
      data_class: dataClass,
      task_budget_usd: Number(taskBudget),
      max_output_tokens: Number(maxOutputTokens),
    };
    try {
      const response = mode === 'parallel'
        ? await axios.post(EXECUTOR_API + '/parallel', { ...common, provider_ids: selected }, { headers })
        : await axios.post(EXECUTOR_API + '/complete', { ...common, provider_id: selected[0] }, { headers });
      setResult(response.data);
      setMessage(mode === 'parallel'
        ? `Lote concluído: ${response.data.success_count} sucesso(s), ${response.data.failure_count} falha(s).`
        : 'Execução concluída.');
    } catch (error) {
      setMessage(error.response?.data?.detail?.message || error.response?.data?.detail || 'A execução não foi concluída.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="ai-provider-executor" aria-labelledby="ai-provider-executor-title">
      <div className="ai-provider-executor-heading">
        <h4 id="ai-provider-executor-title">Executar tarefa de IA</h4>
        <span><ShieldCheck size={14} aria-hidden="true" /> Administração</span>
      </div>
      <p>Use um provedor habilitado e testado ou compare de dois a três em paralelo. O mesmo orçamento máximo vale para o lote inteiro.</p>
      {providers.length === 0 ? (
        <p>Nenhum provedor está habilitado e testado. Cadastre, teste e habilite uma conexão acima.</p>
      ) : (
        <form onSubmit={execute}>
          <label className="display-preference-field">
            <span>Modo</span>
            <select value={mode} disabled={busy} onChange={event => setMode(event.target.value)}>
              <option value="single">Chamada única</option>
              <option value="parallel">Paralelo (2–3 provedores)</option>
            </select>
          </label>
          <label className="display-preference-field">
            <span>Classe dos dados</span>
            <select value={dataClass} disabled={busy} onChange={event => setDataClass(event.target.value)}>
              {DATA_CLASSES.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
            </select>
          </label>
          {mode === 'single' ? (
            <label className="display-preference-field">
              <span>Provedor</span>
              <select value={providerId} disabled={busy} onChange={event => setProviderId(event.target.value)}>
                {eligibleProviders.map(item => <option key={item.id} value={item.id}>{item.name} · {item.model_name}</option>)}
              </select>
            </label>
          ) : (
            <fieldset className="ai-provider-executor-options">
              <legend>Provedores selecionados ({providerIds.length}/3)</legend>
              {eligibleProviders.map(item => (
                <label key={item.id}>
                  <input type="checkbox" checked={providerIds.includes(item.id)} disabled={busy || (!providerIds.includes(item.id) && providerIds.length >= 3)} onChange={() => toggleProvider(item.id)} />
                  <span>{item.name} · {item.model_name}</span>
                </label>
              ))}
              {eligibleProviders.length === 0 && <small>Nenhum provedor permite esta classe de dados.</small>}
            </fieldset>
          )}
          <label className="display-preference-field">
            <span>Instrução <small>(não é salva pelo Nivus)</small></span>
            <textarea value={prompt} maxLength={12000} rows={5} required disabled={busy} onChange={event => setPrompt(event.target.value)} placeholder="Descreva a tarefa. Para provedores em nuvem, use apenas dados públicos ou sintéticos." />
          </label>
          <div className="ai-provider-executor-grid">
            <label className="display-preference-field">
              <span>Orçamento máximo da tarefa (USD)</span>
              <input type="number" min="0" step="0.01" value={taskBudget} disabled={busy} onChange={event => setTaskBudget(event.target.value)} />
            </label>
            <label className="display-preference-field">
              <span>Saída máxima por provedor</span>
              <input type="number" min="1" max="2048" value={maxOutputTokens} disabled={busy} onChange={event => setMaxOutputTokens(event.target.value)} />
            </label>
          </div>
          <label className="display-preference-field">
            <span>ID da tarefa</span>
            <input value={taskId} maxLength={64} disabled={busy} onChange={event => setTaskId(event.target.value)} />
          </label>
          <div className="time-sync-actions">
            <button className="maintenance-toggle" type="submit" disabled={busy || !prompt.trim()}>
              <Play size={15} aria-hidden="true" /> {busy ? 'Executando…' : 'Executar'}
            </button>
            <button className="time-sync-editor-toggle" type="button" disabled={busy} onClick={() => { setTaskId(newTaskId()); setResult(null); setMessage('Novo ID de tarefa criado.'); }}>
              Nova tarefa
            </button>
          </div>
        </form>
      )}
      {result?.output && (
        <article className="ai-provider-executor-result">
          <h5>{result.model || 'Resultado'}</h5>
          <pre>{result.output}</pre>
        </article>
      )}
      {Array.isArray(result?.results) && result.results.map(item => (
        <article className="ai-provider-executor-result" key={item.provider_id}>
          <h5>{providers.find(provider => provider.id === item.provider_id)?.name || item.provider_id} · {item.status}</h5>
          {item.result?.output ? <pre>{item.result.output}</pre> : <p>{item.error?.message || 'Sem saída para esta chamada.'}</p>}
        </article>
      ))}
      <p className="display-preference-save-status" role="status" aria-live="polite">{message}</p>
      <small className="ai-provider-executor-note">Cada provedor pode receber uma chamada; o Nivus não faz retry nem fallback. Resultados ficam apenas nesta tela enquanto ela estiver aberta.</small>
    </section>
  );
}
