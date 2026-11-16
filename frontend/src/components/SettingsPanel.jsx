import React, { useState } from 'react';
import { PauseCircle, PlayCircle, Wrench } from 'lucide-react';
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
}) {
  const enabled = maintenanceState?.enabled === true;
  const offset = formatUtcOffset(displayPreferences.timeZone);
  const [preferenceSaveStatus, setPreferenceSaveStatus] = useState('As preferências são aplicadas imediatamente.');
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
              <p>O relógio do painel atualiza a cada segundo usando o fuso escolhido.</p>
            </div>
            <span className="maintenance-status" role="status">Integração NTP pendente</span>
          </div>
          <p className="settings-explanation">
            Nesta versão, o relógio usa o horário deste navegador e não consulta serviços externos. O estado do NTP do Ubuntu e a configuração redundante de três fontes ainda não estão ligados à API. A futura configuração só será ativada após detectar o cliente NTP existente e preparar backup e rollback; a lista de fontes não será exibida no relógio.
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
