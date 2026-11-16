import React from 'react';
import { Activity, CircleCheck, CircleX, Lock, Unlock } from 'lucide-react';

export default function DashboardHeader({ token, userPayload, fetchData, isOnline, dashboardVersion, onToggleDashboardVersion, isTempCritical = false }) {
  const legacyActive = dashboardVersion === 'legacy';
  const authenticated = Boolean(token);
  const sessionLabel = authenticated ? ('Sessão: ' + userPayload?.sub + ' (' + userPayload?.role + ')') : 'Não Autenticado';

  return (
    <header className="dashboard-header">
      <div className="dashboard-header-title">
        <h1>
          <Activity aria-hidden="true" /> Nivus Edge Dashboard
        </h1>
        <p>Nó: Nivus Edge Node</p>
      </div>
      <div className="dashboard-header-controls">
        <div className="dashboard-header-status-island" aria-label="Estado do Nivus">
          <div
            className={'connection-status ' + (isOnline ? 'connection-status-online' : 'connection-status-offline')}
            role="status"
            aria-live="polite"
            title={isOnline ? 'A API respondeu ao último health check.' : 'A API não respondeu ao último health check.'}
          >
            {isOnline ? <CircleCheck size={14} aria-hidden="true" /> : <CircleX size={14} aria-hidden="true" />}
            <span>{isOnline ? 'API online' : 'API offline'}</span>
          </div>
          <div className="dashboard-auth-status" data-authenticated={authenticated ? 'true' : 'false'}>
            {authenticated ? <Unlock size={14} aria-hidden="true" /> : <Lock size={14} aria-hidden="true" />}
            <span>{sessionLabel}</span>
          </div>
          <div className={'dashboard-header-alert-chip' + (isTempCritical ? ' is-active' : '')} role="status" aria-live="polite">
            {isTempCritical ? 'Alerta térmico' : 'Sem alerta térmico'}
          </div>
        </div>
        <div className="dashboard-header-actions">
          <button
            type="button"
            className="legacy-dashboard-switch"
            aria-pressed={legacyActive}
            aria-label={legacyActive ? 'Voltar para a dashboard atual' : 'Mudar para a versão anterior e leve da dashboard'}
            title={legacyActive ? 'Voltar para a dashboard atual' : 'Abrir a versão anterior e leve da dashboard'}
            onClick={onToggleDashboardVersion}
          >
            <span>{legacyActive ? 'Versão atual' : 'Versão leve'}</span>
            <span className="legacy-dashboard-track" aria-hidden="true"><span /></span>
          </button>
          <button type="button" className="dashboard-refresh-button" onClick={() => fetchData()}>Atualizar</button>
        </div>
      </div>
    </header>
  );
}
