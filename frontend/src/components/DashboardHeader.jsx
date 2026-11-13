import React from 'react';
import { Activity, Lock, Unlock } from 'lucide-react';

export default function DashboardHeader({ token, userPayload, fetchData }) {
  return (
<header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid #334155', paddingBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
            <Activity style={{ color: '#38bdf8' }} /> Nivus Edge Dashboard
          </h1>
          <p style={{ color: '#94a3b8', fontSize: '0.875rem', margin: '0.25rem 0 0 0' }}>Nó: Nivus Edge Node</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', backgroundColor: token ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)', border: `1px solid ${token ? '#10b981' : '#ef4444'}`, padding: '0.4rem 0.8rem', borderRadius: '9999px', fontSize: '0.8rem', color: token ? '#34d399' : '#f87171' }}>
            {token ? <Unlock size={14} /> : <Lock size={14} />}
            <span>{token ? `Sessão: ${userPayload?.sub} (${userPayload?.role})` : 'Não Autenticado'}</span>
          </div>
          <button onClick={() => fetchData()} style={{ backgroundColor: '#3b82f6', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '0.375rem', cursor: 'pointer' }}>Atualizar</button>
        </div>
      </header>
  );
}
