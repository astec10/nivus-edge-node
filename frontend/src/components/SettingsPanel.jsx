import React from 'react';
import { PauseCircle, PlayCircle, Wrench } from 'lucide-react';

function formatStartedAt(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function SettingsPanel({
  maintenanceState,
  maintenanceMessage,
  maintenanceBusy,
  onToggleMaintenance,
}) {
  const enabled = maintenanceState?.enabled === true;

  return (
    <main className="dashboard-content" aria-labelledby="settings-title">
      <section className="dashboard-section" aria-labelledby="settings-title">
        <h2 id="settings-title"><Wrench size={18} aria-hidden="true" /> Configuração</h2>
        <div className="settings-card">
          <div className="settings-card-heading">
            <div>
              <h3>Modo de manutenção</h3>
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

          <p className="maintenance-explanation">
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
        </div>
      </section>
    </main>
  );
}
