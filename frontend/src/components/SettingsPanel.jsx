import React, { useEffect, useState } from 'react';
import { PauseCircle, PlayCircle, RotateCcw, Save, Wrench } from 'lucide-react';
import {
  DASHBOARD_THEMES,
  DATE_FORMATS,
  DEFAULT_DISPLAY_PREFERENCES,
  TIME_ZONES,
  formatUtcOffset,
} from '../utils/displayPreferences';

function formatStartedAt(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function PreferenceField({ label, value, options, onChange, describedBy }) {
  return (
    <label className="display-preference-field">
      <span>{label}</span>
      <select value={value} onChange={event => onChange(event.target.value)} aria-describedby={describedBy}>
        {options.map(option => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </label>
  );
}

export default function SettingsPanel({
  isAdmin = false,
  displayPreferences = DEFAULT_DISPLAY_PREFERENCES,
  onDisplayPreferenceChange = () => {},
  maintenanceState,
  maintenanceMessage,
  maintenanceBusy,
  onToggleMaintenance,
  timeSyncState,
  onApplyTimeSync = async () => ({ ok: false, message: 'Controlador indisponível.' }),
  onRollbackTimeSync = async () => ({ ok: false, message: 'Controlador indisponível.' }),
}) {
  const enabled = maintenanceState?.enabled === true;
  const offset = formatUtcOffset(displayPreferences.timeZone);
  const [preferenceSaveStatus, setPreferenceSaveStatus] = useState('As preferências são aplicadas imediatamente.');
  const suggestedServers = timeSyncState?.suggested_servers?.length === 3
    ? timeSyncState.suggested_servers
    : ['a.ntp.br', 'time.google.com', 'time.cloudflare.com'];
  const configuredServers = timeSyncState?.configured_servers?.length === 3
    ? timeSyncState.configured_servers
    : suggestedServers;
  const hasConfiguredTimeSyncServers = timeSyncState?.configured_servers?.length === 3;
  const timeSyncStatusMessage = timeSyncState?.state === 'managed_elsewhere'
    ? 'Outro cliente de hora está ativo; o Nivus não substitui nem altera essa configuração.'
    : timeSyncState?.state === 'unavailable'
      ? 'systemd-timesyncd não está instalado ou disponível neste host.'
      : timeSyncState?.state === 'inactive'
        ? 'systemd-timesyncd está instalado, mas parado. Aplicar as fontes iniciará esse serviço.'
        : timeSyncState?.state === 'degraded'
          ? 'systemd-timesyncd está ativo, mas ainda não confirmou sincronização.'
          : timeSyncState?.state === 'synchronized'
            ? 'O Ubuntu informa que o relógio está sincronizado.'
            : 'Aguardando o estado do relógio do host.';
  const serverSignature = JSON.stringify(configuredServers);
  const [timeSyncServers, setTimeSyncServers] = useState(suggestedServers);
  const [timeSyncBusy, setTimeSyncBusy] = useState(false);
  const [timeSyncActionMessage, setTimeSyncActionMessage] = useState('');
  useEffect(() => {
    setTimeSyncServers(JSON.parse(serverSignature));
  }, [serverSignature]);
  const timeSyncStatusLabels = {
    synchronized: 'Relógio sincronizado',
    degraded: 'Cliente ativo; sincronização não confirmada',
    unavailable: 'systemd-timesyncd indisponível',
    inactive: 'systemd-timesyncd parado',
    managed_elsewhere: 'Outro cliente de hora está ativo',
  };
  const timeSyncStatusLabel = timeSyncStatusLabels[timeSyncState?.state] || 'Consultando o host…';
  const canConfigureTimeSync = isAdmin && timeSyncState?.can_configure === true;
  const applyTimeSync = async event => {
    event.preventDefault();
    setTimeSyncBusy(true);
    setTimeSyncActionMessage('Aplicando fontes no host…');
    try {
      const result = await onApplyTimeSync(timeSyncServers);
      setTimeSyncActionMessage(result?.ok
        ? (result.data?.message || 'Configuração NTP aplicada.')
        : (result?.message || 'Não foi possível configurar o NTP do host.'));
    } finally {
      setTimeSyncBusy(false);
    }
  };
  const rollbackTimeSync = async () => {
    if (!window.confirm('Restaurar a configuração NTP salva antes da última alteração?')) return;
    setTimeSyncBusy(true);
    setTimeSyncActionMessage('Restaurando a configuração anterior…');
    try {
      const result = await onRollbackTimeSync();
      setTimeSyncActionMessage(result?.ok
        ? (result.data?.message || 'Configuração anterior restaurada.')
        : (result?.message || 'Não foi possível restaurar a configuração anterior.'));
    } finally {
      setTimeSyncBusy(false);
    }
  };
  const updateDisplayPreferences = changes => {
    const saved = onDisplayPreferenceChange(changes);
    setPreferenceSaveStatus(saved
      ? 'Preferências aplicadas e salvas neste navegador para esta conta.'
      : 'Preferências aplicadas nesta sessão; o navegador não permitiu salvá-las localmente.');
  };

  return (
    <main className="dashboard-content" aria-labelledby="settings-title">
      <section className="dashboard-section" aria-labelledby="settings-title">
        <h2 id="settings-title"><Wrench size={18} aria-hidden="true" /> Configuração</h2>

        <section className="settings-card" aria-labelledby="display-settings-title">
          <div className="settings-card-heading">
            <div>
              <h3 id="display-settings-title">Preferências de visualização</h3>
              <p>As alterações são imediatas e ficam neste navegador, separadas por conta, quando o armazenamento local está disponível. O token de acesso nunca é guardado nessas preferências.</p>
            </div>
          </div>

          <div className="display-preference-grid">
            <PreferenceField
              label="Fuso horário"
              value={displayPreferences.timeZone}
              options={TIME_ZONES}
              onChange={timeZone => updateDisplayPreferences({ timeZone })}
              describedBy="timezone-offset"
            />
            <p className="display-preference-hint" id="timezone-offset">
              Diferença atual: {offset}. O horário de verão é resolvido pelo identificador IANA selecionado.
            </p>
            <PreferenceField
              label="Formato da hora"
              value={displayPreferences.timeFormat}
              options={[{ value: '24h', label: '24 horas' }, { value: '12h', label: '12 horas (AM/PM)' }]}
              onChange={timeFormat => updateDisplayPreferences({ timeFormat })}
            />
            <PreferenceField
              label="Formato da data"
              value={displayPreferences.dateFormat}
              options={DATE_FORMATS}
              onChange={dateFormat => updateDisplayPreferences({ dateFormat })}
            />
            <PreferenceField
              label="Tema da dashboard completa"
              value={displayPreferences.theme}
              options={DASHBOARD_THEMES}
              onChange={theme => updateDisplayPreferences({ theme })}
              describedBy="theme-description"
            />
            <p className="display-preference-hint" id="theme-description">
              O tema Atual continua como padrão. A escolha não altera o login nem o seletor completa/leve; a versão leve preserva o visual compacto próprio.
            </p>
          </div>

          <div className="display-preference-toggles">
            <label>
              <input
                type="checkbox"
                checked={displayPreferences.highContrast}
                onChange={event => updateDisplayPreferences({ highContrast: event.target.checked })}
              />
              <span>Contraste alto</span>
            </label>
            <label>
              <input
                type="checkbox"
                checked={displayPreferences.reducedMotion}
                onChange={event => updateDisplayPreferences({ reducedMotion: event.target.checked })}
              />
              <span>Reduzir animações</span>
            </label>
          </div>
          <p className="display-preference-save-status" role="status" aria-live="polite">
            {preferenceSaveStatus}
          </p>
        </section>

        <section className="settings-card" aria-labelledby="time-sync-title">
          <div className="settings-card-heading">
            <div>
              <h3 id="time-sync-title">Sincronização de hora do host</h3>
              <p>Estado observado no Ubuntu. O fuso e os formatos do relógio do painel continuam sendo preferências do navegador.</p>
            </div>
            <span className={"maintenance-status time-sync-status time-sync-status--" + (timeSyncState?.state || 'unknown')} role="status">
              {timeSyncStatusLabel}
            </span>
          </div>

          <p className="settings-explanation">
            A integração usa <strong>a.ntp.br</strong>, <strong>time.google.com</strong> e <strong>time.cloudflare.com</strong>, de provedores distintos. Informe nomes DNS, sem prefixo HTTPS ou porta. Se <code>systemd-timesyncd</code> estiver instalado, mas parado, aplicar as fontes iniciará o serviço; outro cliente ativo (como chrony) continua protegido e não será substituído. O systemd tenta as fontes em sequência, como failover, não votação.
            {' '}<a href="https://www.ntp.br/" target="_blank" rel="noreferrer">NTP.br</a>{' · '}
            <a href="https://developers.google.com/time" target="_blank" rel="noreferrer">Google Public NTP</a>{' · '}
            <a href="https://developers.cloudflare.com/time-services/ntp/usage/" target="_blank" rel="noreferrer">Cloudflare NTP</a>
          </p>

          {isAdmin ? (
            <form className="time-sync-form" onSubmit={applyTimeSync}>
              <div className="time-sync-server-grid">
                {timeSyncServers.map((server, index) => (
                  <label className="display-preference-field" key={index}>
                    <span>Servidor NTP {index + 1}</span>
                    <input
                      type="text"
                      value={server}
                      maxLength={253}
                      autoCapitalize="none"
                      autoCorrect="off"
                      spellCheck="false"
                      placeholder={suggestedServers[index]}
                      onChange={event => setTimeSyncServers(previous => previous.map((value, position) => (
                        position === index ? event.target.value : value
                      )))}
                      disabled={timeSyncBusy || !canConfigureTimeSync}
                    />
                  </label>
                ))}
              </div>
              <div className="time-sync-actions">
                <button
                  className="maintenance-toggle"
                  type="submit"
                  disabled={timeSyncBusy || !canConfigureTimeSync}
                >
                  <Save size={16} aria-hidden="true" />
                  {timeSyncBusy ? 'Aguarde…' : 'Aplicar fontes'}
                </button>
                {timeSyncState?.has_rollback === true && (
                  <button
                    className="maintenance-toggle time-sync-rollback"
                    type="button"
                    disabled={timeSyncBusy || !canConfigureTimeSync}
                    onClick={rollbackTimeSync}
                  >
                    <RotateCcw size={16} aria-hidden="true" />
                    Restaurar configuração anterior
                  </button>
                )}
              </div>
            </form>
          ) : (
            <p className="time-sync-readonly">
              {hasConfiguredTimeSyncServers ? 'Fontes NTP configuradas: ' : 'Sugestões (ainda não configuradas): '}
              {configuredServers.join(', ')}
            </p>
          )}

          <p className="display-preference-save-status" role="status" aria-live="polite">
            {timeSyncActionMessage || timeSyncState?.message || timeSyncStatusMessage}
          </p>
        </section>

        {isAdmin && (
          <section className="settings-card" aria-labelledby="maintenance-title">
            <div className="settings-card-heading">
              <div>
                <h3 id="maintenance-title">Modo de manutenção</h3>
                <p>Reduz o trabalho em segundo plano durante manutenção e diagnóstico.</p>
              </div>
              <span className={`maintenance-status ${enabled ? 'is-active' : ''}`} role="status">
                {maintenanceState ? (enabled ? 'Ativo' : 'Operação normal') : 'Estado indisponível'}
              </span>
            </div>

            {enabled && (
              <dl className="maintenance-details">
                <div><dt>Início</dt><dd>{formatStartedAt(maintenanceState.started_at) || 'Horário indisponível'}</dd></div>
                <div><dt>Em pausa</dt><dd>Coleta do host e gravação de telemetria MQTT</dd></div>
              </dl>
            )}

            <p className="settings-explanation">
              Enquanto ativo, novas leituras não são coletadas nem gravadas. API, login, painel, health checks e broker MQTT continuam ativos. Reiniciar o Ubuntu retorna ao modo normal automaticamente.
            </p>
            <button
              className={`maintenance-toggle ${enabled ? 'is-active' : ''}`}
              type="button"
              aria-pressed={enabled}
              disabled={!maintenanceState || maintenanceBusy}
              onClick={() => onToggleMaintenance(!enabled)}
            >
              {enabled ? <PlayCircle size={17} aria-hidden="true" /> : <PauseCircle size={17} aria-hidden="true" />}
              {maintenanceBusy ? 'Aplicando…' : enabled ? 'Retomar operação normal' : 'Ativar modo de manutenção'}
            </button>
            <p className="maintenance-message" role="status" aria-live="polite">
              {maintenanceMessage || (maintenanceState ? 'Disponível também pelo comando sudo nivusctl maintenance enable|disable.' : 'Confira o estado local com sudo nivusctl maintenance status.')}
            </p>
          </section>
        )}
      </section>
    </main>
  );
}
