import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import AIProviderExecutorPanel from './AIProviderExecutorPanel';
import { Activity, KeyRound, Plus, RefreshCw, ShieldCheck, Trash2 } from 'lucide-react';

const API = '/api/settings/ai-providers';
const DATA_CLASSES = [
  { id: 'public', label: 'Dados públicos' },
  { id: 'synthetic', label: 'Dados sintéticos' },
  { id: 'operational', label: 'Operação do nó' },
  { id: 'personal', label: 'Dados pessoais' },
  { id: 'home', label: 'Telemetria residencial' },
  { id: 'camera', label: 'Imagens e câmeras' },
];
const EMPTY_FORM = {
  provider_type: 'openai',
  name: 'OpenAI',
  protocol: 'openai-compatible',
  endpoint_scope: 'cloud',
  base_url: 'https://api.openai.com/v1',
  model_name: '',
  responsible: '',
  purpose: '',
  auth_method: 'bearer',
  api_key: '',
  monthly_budget_usd: '',
  input_cost_per_million_usd: '',
  output_cost_per_million_usd: '',
  pricing_verified_on: '',
  max_requests_per_hour: '30',
  timeout_seconds: '10',
  allowed_data_classes: ['public', 'synthetic'],
};
const TEST_STATUS = {
  success: 'Conexão confirmada',
  not_tested: 'Ainda não testado',
  credentials_rejected: 'Autenticação recusada',
  rate_limited: 'Limite do provedor',
  budget_required: 'Defina um orçamento mensal antes do teste',
  timeout: 'Tempo esgotado',
  tls_error: 'Falha de certificado TLS',
  redirect_blocked: 'Redirecionamento bloqueado',
  unreachable: 'Endpoint indisponível',
  provider_error: 'Erro do endpoint',
};

function presetForm(providerType, catalog) {
  const item = catalog.find(entry => entry.id === providerType);
  if (!item || item.manual) {
    return {
      ...EMPTY_FORM,
      provider_type: 'manual',
      name: '',
      protocol: item?.protocol || 'openai-compatible',
      endpoint_scope: 'cloud',
      base_url: '',
      auth_method: item?.auth_method || 'bearer',
    };
  }
  return {
    ...EMPTY_FORM,
    provider_type: item.id,
    name: item.name,
    protocol: item.protocol,
    endpoint_scope: item.scope,
    base_url: item.base_url,
    auth_method: item.auth_method,
  };
}

export default function ProviderSettingsPanel({ token }) {
  const headers = useMemo(() => ({ Authorization: 'Bearer ' + token }), [token]);
  const [catalog, setCatalog] = useState([]);
  const [providers, setProviders] = useState([]);
  const [audit, setAudit] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [showForm, setShowForm] = useState(false);
  const [editingProvider, setEditingProvider] = useState(null);
  const [editForm, setEditForm] = useState(null);
  const [credentialFor, setCredentialFor] = useState(null);
  const [replacementKey, setReplacementKey] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [catalogResponse, providerResponse, auditResponse] = await Promise.all([
        axios.get(API + '/catalog', { headers }),
        axios.get(API, { headers }),
        axios.get(API + '/audit?limit=20', { headers }),
      ]);
      setCatalog(Array.isArray(catalogResponse.data) ? catalogResponse.data : []);
      setProviders(Array.isArray(providerResponse.data) ? providerResponse.data : []);
      setAudit(Array.isArray(auditResponse.data) ? auditResponse.data : []);
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Não foi possível carregar os provedores.');
    } finally {
      setLoading(false);
    }
  }, [headers]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const changeProviderType = value => {
    setForm(presetForm(value, catalog));
    setMessage('');
  };

  const changeProtocol = value => {
    const local = value === 'ollama' || form.endpoint_scope === 'local';
    setForm(current => ({
      ...current,
      protocol: value,
      endpoint_scope: local ? 'local' : current.endpoint_scope,
      auth_method: value === 'ollama' || local ? 'none' : (current.auth_method === 'none' ? 'bearer' : current.auth_method),
      api_key: value === 'ollama' || local ? '' : current.api_key,
      base_url: value === 'ollama'
        ? 'http://host.docker.internal:11434'
        : (current.endpoint_scope === 'local' ? 'http://host.docker.internal:1234/v1' : current.base_url),
    }));
  };

  const changeScope = value => {
    setForm(current => ({
      ...current,
      endpoint_scope: value,
      protocol: value === 'local' && current.protocol === 'anthropic' ? 'openai-compatible' : current.protocol,
      auth_method: value === 'local' ? 'none' : (current.auth_method === 'none' ? 'bearer' : current.auth_method),
      api_key: value === 'local' ? '' : current.api_key,
      base_url: value === 'local'
        ? (current.protocol === 'ollama' ? 'http://host.docker.internal:11434' : 'http://host.docker.internal:1234/v1')
        : 'https://',
    }));
  };

  const toggleClass = value => {
    setForm(current => ({
      ...current,
      allowed_data_classes: current.allowed_data_classes.includes(value)
        ? current.allowed_data_classes.filter(item => item !== value)
        : [...current.allowed_data_classes, value],
    }));
  };

  const save = async event => {
    event.preventDefault();
    setBusy(true);
    setMessage('Criptografando e salvando a configuração…');
    const payload = {
      ...form,
      monthly_budget_usd: form.monthly_budget_usd === '' ? null : Number(form.monthly_budget_usd),
      input_cost_per_million_usd: form.input_cost_per_million_usd === '' ? null : Number(form.input_cost_per_million_usd),
      output_cost_per_million_usd: form.output_cost_per_million_usd === '' ? null : Number(form.output_cost_per_million_usd),
      pricing_verified_on: form.pricing_verified_on || null,
      max_requests_per_hour: Number(form.max_requests_per_hour),
      timeout_seconds: Number(form.timeout_seconds),
      ...(form.api_key.trim() ? { api_key: form.api_key } : {}),
    };
    try {
      await axios.post(API, payload, { headers });
      setForm(EMPTY_FORM);
      setShowForm(false);
      setMessage('Provedor cadastrado. A chave não será exibida novamente.');
      await refresh();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Não foi possível cadastrar o provedor.');
    } finally {
      setBusy(false);
    }
  };

  const testProvider = async provider => {
    if (provider.endpoint_scope === 'cloud'
      && !window.confirm('O teste envia somente uma consulta GET de modelos e a chave de API ao provedor. Nenhum prompt ou dado do Nivus será enviado. A chamada pode consumir cota. Continuar?')) return;
    setBusy(true);
    setMessage('Testando endpoint sem enviar prompts…');
    try {
      const response = await axios.post(API + '/' + provider.id + '/test', null, { headers });
      setMessage(response.data.message || 'Teste concluído.');
      await refresh();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Não foi possível testar esta conexão.');
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const toggleProvider = async provider => {
    setBusy(true);
    try {
      await axios.post(API + '/' + provider.id + '/enabled', { enabled: !provider.enabled }, { headers });
      setMessage(provider.enabled
        ? 'Provedor desabilitado.'
        : 'Provedor habilitado; cada execução ainda precisa respeitar os limites e a classe de dados permitida.');
      await refresh();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Não foi possível alterar o estado.');
    } finally {
      setBusy(false);
    }
  };

  const removeProvider = async provider => {
    if (!window.confirm('Remover a conexão e a chave cifrada deste provedor? O registro de auditoria permanecerá sem o segredo.')) return;
    setBusy(true);
    try {
      await axios.delete(API + '/' + provider.id, { headers });
      setMessage('Provedor removido.');
      await refresh();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Não foi possível remover o provedor.');
    } finally {
      setBusy(false);
    }
  };

  const replaceKey = async event => {
    event.preventDefault();
    if (!credentialFor || !replacementKey.trim()) return;
    setBusy(true);
    try {
      await axios.put(API + '/' + credentialFor + '/credential', { api_key: replacementKey }, { headers });
      setCredentialFor(null);
      setReplacementKey('');
      setMessage('Chave substituída. O provedor foi desabilitado e precisa ser testado de novo.');
      await refresh();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Não foi possível substituir a chave.');
    } finally {
      setBusy(false);
    }
  };

  const startEditing = provider => {
    setShowForm(false);
    setEditingProvider(provider.id);
    setCredentialFor(null);
    setReplacementKey('');
    setEditForm({
      name: provider.name,
      model_name: provider.model_name,
      responsible: provider.responsible,
      purpose: provider.purpose,
      monthly_budget_usd: provider.monthly_budget_usd == null ? '' : String(provider.monthly_budget_usd),
      input_cost_per_million_usd: provider.input_cost_per_million_usd == null ? '' : String(provider.input_cost_per_million_usd),
      output_cost_per_million_usd: provider.output_cost_per_million_usd == null ? '' : String(provider.output_cost_per_million_usd),
      pricing_verified_on: provider.pricing_verified_on || '',
      max_requests_per_hour: String(provider.max_requests_per_hour),
      timeout_seconds: String(provider.timeout_seconds),
      allowed_data_classes: provider.allowed_data_classes || [],
    });
    setMessage('');
  };

  const toggleEditClass = value => {
    setEditForm(current => ({
      ...current,
      allowed_data_classes: current.allowed_data_classes.includes(value)
        ? current.allowed_data_classes.filter(item => item !== value)
        : [...current.allowed_data_classes, value],
    }));
  };

  const saveMetadata = async event => {
    event.preventDefault();
    if (!editingProvider || !editForm) return;
    setBusy(true);
    setMessage('Salvando alterações do cadastro…');
    try {
      await axios.patch(API + '/' + editingProvider, {
        name: editForm.name,
        model_name: editForm.model_name,
        responsible: editForm.responsible,
        purpose: editForm.purpose,
        monthly_budget_usd: editForm.monthly_budget_usd === '' ? null : Number(editForm.monthly_budget_usd),
        input_cost_per_million_usd: editForm.input_cost_per_million_usd === '' ? null : Number(editForm.input_cost_per_million_usd),
        output_cost_per_million_usd: editForm.output_cost_per_million_usd === '' ? null : Number(editForm.output_cost_per_million_usd),
        pricing_verified_on: editForm.pricing_verified_on || null,
        max_requests_per_hour: Number(editForm.max_requests_per_hour),
        timeout_seconds: Number(editForm.timeout_seconds),
        allowed_data_classes: editForm.allowed_data_classes,
      }, { headers });
      setEditingProvider(null);
      setEditForm(null);
      setMessage('Cadastro atualizado. O endpoint e o protocolo não foram alterados.');
      await refresh();
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Não foi possível atualizar o cadastro.');
    } finally {
      setBusy(false);
    }
  };

  const manual = form.provider_type === 'manual';
  const visibleClasses = DATA_CLASSES.filter(item => (
    form.endpoint_scope === 'local' || ['public', 'synthetic'].includes(item.id)
  ));

  return (
    <section className="settings-card provider-settings" aria-labelledby="provider-settings-title">
      <div className="settings-card-heading">
        <div>
          <h3 id="provider-settings-title">Provedores de IA para executores</h3>
          <p>Cadastre provedores do runtime Nivus, com responsável, finalidade, modelo e limites definidos.</p>
        </div>
        <span className="maintenance-status" role="status">
          <ShieldCheck size={14} aria-hidden="true" /> Somente administradores
        </span>
      </div>

      <div className="provider-security-note">
        <KeyRound size={17} aria-hidden="true" />
        <p>
          Chaves são cifradas no servidor com AES-GCM e uma chave mestra fora do SQLite e do repositório.
          A API nunca devolve a chave. Guarde um backup protegido da chave mestra separado do backup do banco.
          Esse cadastro é separado do segredo <code>GEMINI_API_KEY</code> do GitHub Actions.
        </p>
      </div>
      <p className="settings-explanation">
        Salvar não faz uma chamada externa. O teste é manual, consulta apenas a lista de modelos e não envia prompts.
        Nuvem aceita somente dados públicos ou sintéticos; endpoints locais ficam limitados a portas de modelos conhecidas.
        Antes da inferência, o executor verifica classe de dados, preços conferidos nos últimos 90 dias, orçamento mensal,
        orçamento da tarefa, limite por hora e timeout. Sem preço atual ou orçamento, a chamada é bloqueada.
      </p>

      <div className="provider-toolbar">
        <button className="maintenance-toggle" type="button" disabled={loading || busy || catalog.length === 0} onClick={() => { const next = !showForm; setShowForm(next); if (next) { setEditingProvider(null); setEditForm(null); setCredentialFor(null); setReplacementKey(''); } setMessage(''); }}>
          <Plus size={16} aria-hidden="true" />
          {showForm ? 'Fechar cadastro' : 'Adicionar provedor'}
        </button>
        <button className="time-sync-editor-toggle" type="button" onClick={() => void refresh()} disabled={loading || busy}>
          <RefreshCw size={15} aria-hidden="true" /> Atualizar lista
        </button>
      </div>

      {showForm && (
        <form className="provider-form" onSubmit={save}>
          <h4>Novo cadastro</h4>
          <label className="display-preference-field">
            <span>Serviço ou provedor</span>
            <select value={form.provider_type} onChange={event => changeProviderType(event.target.value)}>
              {catalog.map(item => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </label>

          {manual && (
            <>
              <div className="provider-fields-grid">
                <label className="display-preference-field">
                  <span>Nome do serviço</span>
                  <input value={form.name} maxLength={80} required onChange={event => setForm({ ...form, name: event.target.value })} />
                </label>
                <label className="display-preference-field">
                  <span>Tipo de endpoint</span>
                  <select value={form.endpoint_scope} onChange={event => changeScope(event.target.value)}>
                    <option value="cloud">Nuvem (HTTPS público)</option>
                    <option value="local">Modelo local na LAN</option>
                  </select>
                </label>
                <label className="display-preference-field">
                  <span>Protocolo</span>
                  <select value={form.protocol} onChange={event => changeProtocol(event.target.value)}>
                    <option value="openai-compatible">API compatível com OpenAI</option>
                    {form.endpoint_scope === 'local' && <option value="ollama">Ollama</option>}
                  </select>
                </label>
                <label className="display-preference-field provider-wide-field">
                  <span>URL-base</span>
                  <input type="url" value={form.base_url} maxLength={512} required autoCapitalize="none" autoCorrect="off" spellCheck="false" onChange={event => setForm({ ...form, base_url: event.target.value })} />
                </label>
              </div>
              <p className="provider-inline-note">
                {form.endpoint_scope === 'local'
                  ? 'Endpoint local: HTTP privado, portas permitidas para Ollama (11434), LM Studio (1234) ou vLLM (8000).'
                  : 'Endpoint manual de nuvem: HTTPS na porta 443. Confira o domínio antes de enviar uma chave.'}
              </p>
            </>
          )}

          <div className="provider-fields-grid">
            <label className="display-preference-field">
              <span>Modelo</span>
              <input value={form.model_name} maxLength={128} required placeholder="Ex.: modelo disponível na sua conta" onChange={event => setForm({ ...form, model_name: event.target.value })} />
            </label>
            <label className="display-preference-field">
              <span>Responsável pelo serviço / cobrança</span>
              <input value={form.responsible} maxLength={80} required placeholder="Pessoa, equipe ou conta responsável" onChange={event => setForm({ ...form, responsible: event.target.value })} />
            </label>
            <label className="display-preference-field provider-wide-field">
              <span>Finalidade</span>
              <input value={form.purpose} maxLength={500} required placeholder="Para quais tarefas este conector poderá ser usado?" onChange={event => setForm({ ...form, purpose: event.target.value })} />
            </label>
            {form.auth_method !== 'none' && (
              <label className="display-preference-field provider-wide-field">
                <span>Chave de API (mostrada somente enquanto digita)</span>
                <input type="password" value={form.api_key} maxLength={4096} required autoComplete="new-password" autoCapitalize="none" spellCheck="false" onChange={event => setForm({ ...form, api_key: event.target.value })} />
              </label>
            )}
            {manual && form.endpoint_scope === 'cloud' && (
              <label className="display-preference-field">
                <span>Método de autenticação</span>
                <select value={form.auth_method} onChange={event => setForm({ ...form, auth_method: event.target.value, api_key: '' })}>
                  <option value="bearer">Bearer token</option>
                  <option value="x-api-key">x-api-key</option>
                  <option value="google-api-key">Google API key header</option>
                  <option value="none">Sem chave</option>
                </select>
              </label>
            )}
            {form.endpoint_scope === 'cloud' && (
              <label className="display-preference-field">
                <span>Limite mensal (USD)</span>
                <input type="number" min="0.01" step="0.01" required value={form.monthly_budget_usd} onChange={event => setForm({ ...form, monthly_budget_usd: event.target.value })} />
              </label>
            )}
            {form.endpoint_scope === 'cloud' && (
              <>
                <label className="display-preference-field">
                  <span>Entrada por 1 milhão de tokens (USD)</span>
                  <input type="number" min="0" step="any" value={form.input_cost_per_million_usd} onChange={event => setForm({ ...form, input_cost_per_million_usd: event.target.value })} />
                </label>
                <label className="display-preference-field">
                  <span>Saída por 1 milhão de tokens (USD)</span>
                  <input type="number" min="0" step="any" value={form.output_cost_per_million_usd} onChange={event => setForm({ ...form, output_cost_per_million_usd: event.target.value })} />
                </label>
                <label className="display-preference-field">
                  <span>Data da conferência de preços</span>
                  <input type="date" value={form.pricing_verified_on} onChange={event => setForm({ ...form, pricing_verified_on: event.target.value })} />
                </label>
                <p className="provider-inline-note provider-wide-field">
                  Informe os preços oficiais do modelo. A inferência em nuvem fica bloqueada sem os dois valores e uma data de conferência com até 90 dias.
                </p>
              </>
            )}
            <label className="display-preference-field">
              <span>Limite de solicitações por hora</span>
              <input type="number" min="1" max="10000" value={form.max_requests_per_hour} onChange={event => setForm({ ...form, max_requests_per_hour: event.target.value })} />
            </label>
            <label className="display-preference-field">
              <span>Timeout (segundos)</span>
              <input type="number" min="2" max="60" value={form.timeout_seconds} onChange={event => setForm({ ...form, timeout_seconds: event.target.value })} />
            </label>
          </div>

          <fieldset className="provider-data-policy">
            <legend>Dados permitidos para este provedor</legend>
            <div className="provider-data-options">
              {visibleClasses.map(item => (
                <label key={item.id}>
                  <input type="checkbox" checked={form.allowed_data_classes.includes(item.id)} onChange={() => toggleClass(item.id)} />
                  <span>{item.label}</span>
                </label>
              ))}
            </div>
            {form.endpoint_scope === 'cloud' && (
              <small>Para nuvem, dados operacionais, pessoais, residenciais e de câmera permanecem bloqueados.</small>
            )}
          </fieldset>

          <div className="time-sync-actions">
            <button className="maintenance-toggle" type="submit" disabled={busy}>
              {busy ? 'Salvando…' : 'Salvar desabilitado'}
            </button>
            <button className="time-sync-editor-toggle" type="button" disabled={busy} onClick={() => { setShowForm(false); setForm(EMPTY_FORM); }}>
              Cancelar
            </button>
          </div>
        </form>
      )}

      <div className="provider-list">
        <h4>Conexões cadastradas</h4>
        {loading ? <p>Carregando conexões…</p> : providers.length === 0 ? (
          <p>Nenhum provedor cadastrado. Adicione um serviço para começar.</p>
        ) : providers.map(provider => (
          <article className="provider-entry" key={provider.id}>
            <div className="provider-entry-heading">
              <div>
                <h5>{provider.name} <span className="provider-model">{provider.model_name}</span></h5>
                <p>{provider.responsible} · {provider.endpoint_scope === 'local' ? 'Modelo local' : 'Nuvem'} · {provider.purpose}</p>
              </div>
              <span className={'maintenance-status ' + (provider.enabled ? 'is-active' : '')}>
                {provider.enabled ? 'Habilitado' : 'Desabilitado'}
              </span>
            </div>
            <dl className="provider-metadata">
              <div><dt>Endpoint</dt><dd>{provider.base_url}</dd></div>
              <div><dt>Chave</dt><dd>{provider.credential_configured ? 'Configurada · ••••••••' : 'Não configurada'}</dd></div>
              <div><dt>Teste</dt><dd>{TEST_STATUS[provider.last_test_status] || provider.last_test_status}</dd></div>
              <div><dt>Dados permitidos</dt><dd>{provider.allowed_data_classes.join(', ')}</dd></div>
              {provider.endpoint_scope === 'cloud' && <div><dt>Limite mensal</dt><dd>{provider.monthly_budget_usd == null ? 'Não definido' : 'US$ ' + Number(provider.monthly_budget_usd).toFixed(2)}</dd></div>}
              {provider.endpoint_scope === 'cloud' && (
                <div><dt>Preços confirmados</dt><dd>
                  {provider.input_cost_per_million_usd == null || provider.output_cost_per_million_usd == null || !provider.pricing_verified_on
                    ? 'Não configurados'
                    : `Entrada US$ ${provider.input_cost_per_million_usd}/M · saída US$ ${provider.output_cost_per_million_usd}/M · conferidos em ${provider.pricing_verified_on}`}
                </dd></div>
              )}
              <div><dt>Máx./hora</dt><dd>{provider.max_requests_per_hour}</dd></div>
            </dl>
            <div className="provider-actions">
              <button type="button" className="time-sync-editor-toggle" disabled={busy} onClick={() => void testProvider(provider)}>
                <Activity size={15} aria-hidden="true" /> Testar conexão
              </button>
              <button type="button" className="time-sync-editor-toggle" disabled={busy || provider.last_test_status !== 'success'} onClick={() => void toggleProvider(provider)}>
                {provider.enabled ? 'Desabilitar' : 'Habilitar'}
              </button>
              {provider.credential_configured && (
                <button type="button" className="time-sync-editor-toggle" disabled={busy} onClick={() => { setEditingProvider(null); setEditForm(null); setCredentialFor(credentialFor === provider.id ? null : provider.id); setReplacementKey(''); }}>
                  <KeyRound size={15} aria-hidden="true" /> Substituir chave
                </button>
              )}
              <button type="button" className="time-sync-editor-toggle" disabled={busy} onClick={() => startEditing(provider)}>Editar cadastro</button>
              <button type="button" className="provider-delete-button" disabled={busy} onClick={() => void removeProvider(provider)}>
                <Trash2 size={15} aria-hidden="true" /> Remover
              </button>
            </div>
            {editingProvider === provider.id && editForm && (
              <form className="provider-metadata-editor" onSubmit={saveMetadata}>
                <h6>Editar dados do cadastro</h6>
                <p>O endpoint e o protocolo permanecem fixos. Para trocar a URL, remova esta conexão e cadastre-a novamente. A chave fica em um fluxo separado.</p>
                <div className="provider-fields-grid">
                  <label className="display-preference-field">
                    <span>Nome</span>
                    <input value={editForm.name} maxLength={80} required onChange={event => setEditForm({ ...editForm, name: event.target.value })} />
                  </label>
                  <label className="display-preference-field">
                    <span>Modelo</span>
                    <input value={editForm.model_name} maxLength={128} required onChange={event => setEditForm({ ...editForm, model_name: event.target.value })} />
                  </label>
                  <label className="display-preference-field">
                    <span>Responsável pelo serviço / cobrança</span>
                    <input value={editForm.responsible} maxLength={80} required onChange={event => setEditForm({ ...editForm, responsible: event.target.value })} />
                  </label>
                  <label className="display-preference-field provider-wide-field">
                    <span>Finalidade</span>
                    <input value={editForm.purpose} maxLength={500} required onChange={event => setEditForm({ ...editForm, purpose: event.target.value })} />
                  </label>
                  {provider.endpoint_scope === 'cloud' && (
                    <label className="display-preference-field">
                      <span>Limite mensal (USD)</span>
                      <input type="number" min="0.01" step="0.01" required value={editForm.monthly_budget_usd} onChange={event => setEditForm({ ...editForm, monthly_budget_usd: event.target.value })} />
                    </label>
                  )}
                  {provider.endpoint_scope === 'cloud' && (
                    <>
                      <label className="display-preference-field">
                        <span>Entrada por 1 milhão de tokens (USD)</span>
                        <input type="number" min="0" step="any" value={editForm.input_cost_per_million_usd} onChange={event => setEditForm({ ...editForm, input_cost_per_million_usd: event.target.value })} />
                      </label>
                      <label className="display-preference-field">
                        <span>Saída por 1 milhão de tokens (USD)</span>
                        <input type="number" min="0" step="any" value={editForm.output_cost_per_million_usd} onChange={event => setEditForm({ ...editForm, output_cost_per_million_usd: event.target.value })} />
                      </label>
                      <label className="display-preference-field">
                        <span>Data da conferência de preços</span>
                        <input type="date" value={editForm.pricing_verified_on} onChange={event => setEditForm({ ...editForm, pricing_verified_on: event.target.value })} />
                      </label>
                    </>
                  )}
                  <label className="display-preference-field">
                    <span>Limite de solicitações por hora</span>
                    <input type="number" min="1" max="10000" value={editForm.max_requests_per_hour} onChange={event => setEditForm({ ...editForm, max_requests_per_hour: event.target.value })} />
                  </label>
                  <label className="display-preference-field">
                    <span>Timeout (segundos)</span>
                    <input type="number" min="2" max="60" value={editForm.timeout_seconds} onChange={event => setEditForm({ ...editForm, timeout_seconds: event.target.value })} />
                  </label>
                </div>
                <fieldset className="provider-data-policy">
                  <legend>Dados permitidos</legend>
                  <div className="provider-data-options">
                    {DATA_CLASSES.filter(item => provider.endpoint_scope === 'local' || ['public', 'synthetic'].includes(item.id)).map(item => (
                      <label key={item.id}>
                        <input type="checkbox" checked={editForm.allowed_data_classes.includes(item.id)} onChange={() => toggleEditClass(item.id)} />
                        <span>{item.label}</span>
                      </label>
                    ))}
                  </div>
                  {provider.endpoint_scope === 'cloud' && <small>Os conectores de nuvem permanecem limitados a dados públicos ou sintéticos.</small>}
                </fieldset>
                <div className="time-sync-actions">
                  <button className="maintenance-toggle" type="submit" disabled={busy}>{busy ? 'Salvando…' : 'Salvar alterações'}</button>
                  <button className="time-sync-editor-toggle" type="button" disabled={busy} onClick={() => { setEditingProvider(null); setEditForm(null); }}>Cancelar</button>
                </div>
              </form>
            )}
            {credentialFor === provider.id && (
              <form className="provider-replace-key" onSubmit={replaceKey}>
                <label className="display-preference-field">
                  <span>Nova chave de API</span>
                  <input type="password" autoComplete="new-password" value={replacementKey} onChange={event => setReplacementKey(event.target.value)} required />
                </label>
                <button className="maintenance-toggle" type="submit" disabled={busy}>{busy ? 'Salvando…' : 'Salvar nova chave'}</button>
              </form>
            )}
          </article>
        ))}
      </div>

      <details className="provider-audit">
        <summary>Auditoria recente (sem chaves ou prompts)</summary>
        {audit.length === 0 ? <p>Nenhuma alteração registrada.</p> : (
          <ul>{audit.map((entry, index) => (
            <li key={entry.created_at + '-' + index}>
              {new Date(entry.created_at * 1000).toLocaleString()} · {entry.actor} · {entry.action} · {entry.outcome}
            </li>
          ))}</ul>
        )}
      </details>
      <p className="display-preference-save-status" role="status" aria-live="polite">{message}</p>
      <AIProviderExecutorPanel token={token} />
    </section>
  );
}
