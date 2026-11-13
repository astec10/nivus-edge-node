import React from 'react';
import { Users } from 'lucide-react';

export default function DashboardNavigation({ token, isAdmin, activeTab, setActiveTab, handleLogout }) {
  return (
    <>
      {token && (
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', borderBottom: '1px solid #334155', paddingBottom: '0.75rem' }}>
          <button onClick={() => setActiveTab('dashboard')} style={{ backgroundColor: activeTab === 'dashboard' ? '#38bdf8' : '#1e293b', color: activeTab === 'dashboard' ? '#0f172a' : '#f8fafc', border: '1px solid #334155', padding: '0.5rem 1.2rem', borderRadius: '0.375rem', cursor: 'pointer', fontWeight: '600' }}>📊 Painel</button>
          {isAdmin && (
            <button onClick={() => setActiveTab('users')} style={{ backgroundColor: activeTab === 'users' ? '#a855f7' : '#1e293b', color: '#ffffff', border: '1px solid #334155', padding: '0.5rem 1.2rem', borderRadius: '0.375rem', cursor: 'pointer', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Users size={16} /> Gestão de Utilizadores
            </button>
          )}
          <button onClick={handleLogout} style={{ marginLeft: 'auto', backgroundColor: 'transparent', border: '1px solid #ef4444', color: '#f87171', padding: '0.4rem 0.8rem', borderRadius: '0.375rem', cursor: 'pointer' }}>Terminar Sessão</button>
        </div>
      )}
    </>
  );
}
