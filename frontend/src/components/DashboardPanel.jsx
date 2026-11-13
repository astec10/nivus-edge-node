import React from 'react';
import { Activity, Zap, Settings, Terminal } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function DashboardPanel({ activeTab, error, latest, settings, setSettings, isAdmin, handleUpdateSetting, telemetry, controlMode, setControlMode, relayState, handleRelayToggle, systemLogs }) {
  return (
    <>
      {activeTab === 'dashboard' && (
        <>
          {error && <div style={{ backgroundColor: '#7f1d1d', color: '#fca5a5', padding: '1rem', borderRadius: '0.5rem', marginBottom: '1.5rem' }}>{error}</div>}
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
            <div style={{ backgroundColor: '#1e293b', padding: '1.25rem', borderRadius: '0.75rem', border: '1px solid #334155' }}>
              <span style={{ color: '#94a3b8' }}>CPU</span>
              <div style={{ fontSize: '1.8rem', fontWeight: 'bold' }}>{latest ? `${latest.cpu_percent}%` : 'N/A'}</div>
            </div>
            <div style={{ backgroundColor: '#1e293b', padding: '1.25rem', borderRadius: '0.75rem', border: '1px solid #334155' }}>
              <span style={{ color: '#94a3b8' }}>Memória</span>
              <div style={{ fontSize: '1.8rem', fontWeight: 'bold' }}>{latest ? `${latest.memory_percent}%` : 'N/A'}</div>
            </div>
            <div style={{ backgroundColor: '#1e293b', padding: '1.25rem', borderRadius: '0.75rem', border: '1px solid #334155' }}>
              <span style={{ color: '#94a3b8' }}>Disco</span>
              <div style={{ fontSize: '1.8rem', fontWeight: 'bold' }}>{latest ? `${latest.disk_percent}%` : 'N/A'}</div>
            </div>
            <div style={{ backgroundColor: '#1e293b', padding: '1.25rem', borderRadius: '0.75rem', border: '1px solid #334155' }}>
              <span style={{ color: '#94a3b8' }}>Temperatura</span>
              <div style={{ fontSize: '1.8rem', fontWeight: 'bold' }}>{latest ? `${latest.temperature}°C` : 'N/A'}</div>
            </div>
            <div style={{ backgroundColor: '#1e293b', padding: '1.25rem', borderRadius: '0.75rem', border: '1px solid #334155' }}>
              <span style={{ color: '#94a3b8' }}>Energia</span>
              <div style={{ fontSize: '1.8rem', fontWeight: 'bold' }}>{latest ? `${latest.power_consumption}W` : 'N/A'}</div>
            </div>
          </div>

          <div style={{ backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.75rem', border: '1px solid #334155', marginBottom: '2rem' }}>
            <h3 style={{ marginTop: 0, color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Activity style={{ color: '#38bdf8' }} /> Telemetria em Tempo Real (Temperatura, Uso e Consumo)
            </h3>
            <div style={{ width: '100%', height: '300px', marginTop: '1rem' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={telemetry}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="time" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }} />
                  <Legend />
                  <Line type="monotone" dataKey="temperature" name="Temperatura (°C)" stroke="#ef4444" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="cpu_percent" name="Uso CPU (%)" stroke="#38bdf8" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="power_consumption" name="Consumo (W)" stroke="#10b981" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '2rem', marginBottom: '2rem' }}>
            <div style={{ backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.75rem', border: '1px solid #334155' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ margin: 0, color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Zap size={18} style={{ color: '#eab308' }} /> Atuadores (MQTT)
                </h3>
                <div style={{ display: 'flex', backgroundColor: '#0f172a', borderRadius: '0.375rem', padding: '0.2rem', border: '1px solid #334155' }}>
                  <button onClick={() => setControlMode('auto')} style={{ backgroundColor: controlMode === 'auto' ? '#3b82f6' : 'transparent', color: 'white', border: 'none', padding: '0.3rem 0.7rem', borderRadius: '0.25rem', fontSize: '0.8rem', cursor: 'pointer', fontWeight: '600' }}>Auto</button>
                  <button onClick={() => setControlMode('manual')} style={{ backgroundColor: controlMode === 'manual' ? '#3b82f6' : 'transparent', color: 'white', border: 'none', padding: '0.3rem 0.7rem', borderRadius: '0.25rem', fontSize: '0.8rem', cursor: 'pointer', fontWeight: '600' }}>Manual</button>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#0f172a', padding: '1rem', borderRadius: '0.5rem', border: '1px solid #334155' }}>
                <div>
                  <div style={{ fontWeight: '500', fontSize: '0.95rem' }}>Relé Principal (Carga)</div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{controlMode === 'auto' ? 'Modo Automático ativo' : 'Modo Manual ativo'}</div>
                </div>
                <div onClick={controlMode === 'manual' && isAdmin ? handleRelayToggle : undefined} style={{ width: '56px', height: '28px', backgroundColor: relayState ? '#10b981' : '#475569', borderRadius: '14px', position: 'relative', cursor: controlMode === 'manual' && isAdmin ? 'pointer' : 'not-allowed', transition: 'background-color 0.2s', opacity: controlMode === 'auto' ? 0.6 : 1 }}>
                  <div style={{ width: '22px', height: '22px', backgroundColor: 'white', borderRadius: '50%', position: 'absolute', top: '3px', left: relayState ? '31px' : '3px', transition: 'left 0.2s', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }} />
                </div>
              </div>
            </div>

            <div style={{ backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.75rem', border: '1px solid #334155' }}>
              <h3 style={{ marginTop: 0, color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Settings size={18} /> Limiares de Alerta
              </h3>
              <div style={{ marginBottom: '0.5rem' }}>
                <label style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Temperatura Limite (°C):</label>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.3rem' }}>
                  <input type="number" disabled={!isAdmin} value={settings.temp_threshold} onChange={e => setSettings({ ...settings, temp_threshold: e.target.value })} style={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: 'white', padding: '0.4rem', borderRadius: '0.375rem', width: '100%' }} />
                  {isAdmin && <button onClick={() => handleUpdateSetting('temp_threshold', settings.temp_threshold)} style={{ backgroundColor: '#a855f7', color: 'white', border: 'none', padding: '0.4rem 0.8rem', borderRadius: '0.375rem', cursor: 'pointer' }}>Salvar</button>}
                </div>
              </div>
            </div>
          </div>

          <div style={{ backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.75rem', border: '1px solid #334155' }}>
            <h3 style={{ marginTop: 0, color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Terminal size={18} /> Logs do Sistema
            </h3>
            <div style={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '0.5rem', padding: '1rem', height: '160px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.85rem', color: '#38bdf8' }}>
              {systemLogs.map((log, i) => <div key={i}>{log}</div>)}
            </div>
          </div>
        </>
      )}
    </>
  );
}