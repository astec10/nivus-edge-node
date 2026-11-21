import React from 'react';
import { Network, Settings, Users } from 'lucide-react';
import ClockDisplay from './ClockDisplay';
import { DEFAULT_DISPLAY_PREFERENCES } from '../utils/displayPreferences';

function NavigationButton({ active, className = '', onClick, children, label }) {
  return (
    <button
      type="button"
      className={`dashboard-nav-button ${className} ${active ? 'is-active' : ''}`}
      aria-current={active ? 'page' : undefined}
      onClick={onClick}
    >
      {label && <span className="dashboard-nav-button__icon" aria-hidden="true">{label}</span>}
      {children}
    </button>
  );
}

export default function DashboardNavigation({
  token,
  isAdmin,
  activeTab,
  setActiveTab,
  handleLogout,
  displayPreferences = DEFAULT_DISPLAY_PREFERENCES,
}) {
  if (!token) return null;

  return (
    <nav className="dashboard-navigation" aria-label="Navegação principal">
      <NavigationButton active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} label="▦">
        Painel
      </NavigationButton>
      {isAdmin && (
        <NavigationButton
          active={activeTab === 'users'}
          className="dashboard-nav-button--users"
          onClick={() => setActiveTab('users')}
        >
          <Users size={16} aria-hidden="true" /> Gestão de Utilizadores
        </NavigationButton>
      )}
      {isAdmin && (
        <NavigationButton
          active={activeTab === 'nodes'}
          className="dashboard-nav-button--nodes"
          onClick={() => setActiveTab('nodes')}
        >
          <Network size={16} aria-hidden="true" /> Nós
        </NavigationButton>
      )}
      <ClockDisplay preferences={displayPreferences} />
      <NavigationButton active={activeTab === 'settings'} onClick={() => setActiveTab('settings')}>
        <Settings size={16} aria-hidden="true" /> Configuração
      </NavigationButton>
      <button className="dashboard-nav-logout" type="button" onClick={handleLogout}>
        Terminar Sessão
      </button>
    </nav>
  );
}
