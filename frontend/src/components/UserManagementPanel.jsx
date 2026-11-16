import React from 'react';
import { Users, UserPlus, Edit3, Trash2 } from 'lucide-react';

export default function UserManagementPanel({ token, isAdmin, activeTab, newUsername, setNewUsername, newPassword, setNewPassword, newRole, setNewRole, handleSaveUser, usersList, setEditingUser, setTargetNewPassword, setTargetConfirmPassword, setAdminAuthPassword, handleDeleteUser }) {
  return (
    <>
      {token && isAdmin && activeTab === 'users' && (
        <div className="user-management-panel" style={{ backgroundColor: '#1e293b', border: '1px solid #334155', padding: '2rem', borderRadius: '0.75rem', marginBottom: '2rem' }}>
          <h2 style={{ marginTop: 0, color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Users style={{ color: '#a855f7' }} /> Gestão de Utilizadores e Credenciais
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '2rem' }}>
            
            <div className="user-management-card" style={{ backgroundColor: '#0f172a', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #334155' }}>
              <h3 style={{ marginTop: 0, color: '#38bdf8' }}><UserPlus size={18} /> Registar Novo Utilizador</h3>
              <form onSubmit={handleSaveUser} autoComplete="off">
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Nome de Utilizador:</label>
                  <input type="text" value={newUsername} onChange={e => setNewUsername(e.target.value)} minLength={1} maxLength={32} pattern="^[A-Za-z0-9_.-]+$" autoComplete="off" title="Use letras, números, ponto, hífen ou sublinhado (1–32 caracteres)." required style={{ width: '100%', backgroundColor: '#1e293b', border: '1px solid #334155', color: 'white', padding: '0.5rem', borderRadius: '0.375rem' }} />
                </div>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Senha temporária inicial:</label>
                  <input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} minLength={8} maxLength={256} autoComplete="new-password" aria-describedby="new-user-password-hint" title="Mínimo 8 caracteres, com uma letra e um número." required style={{ width: '100%', backgroundColor: '#1e293b', border: '1px solid #334155', color: 'white', padding: '0.5rem', borderRadius: '0.375rem' }} />
                  <p id="new-user-password-hint" style={{ color: '#94a3b8', fontSize: '0.75rem', margin: '0.35rem 0 0' }}>Senha temporária: mínimo de 8 caracteres, com pelo menos uma letra e um número. O utilizador terá de trocá-la no primeiro acesso.</p>
                </div>
                <div style={{ marginBottom: '1.25rem' }}>
                  <label style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Nível de Privilégio:</label>
                  <select value={newRole} onChange={e => setNewRole(e.target.value)} style={{ width: '100%', backgroundColor: '#1e293b', border: '1px solid #334155', color: 'white', padding: '0.5rem', borderRadius: '0.375rem' }}>
                    <option value="viewer">Viewer (Apenas Leitura)</option>
                    <option value="admin">Administrador (Total)</option>
                  </select>
                </div>
                <button type="submit" style={{ backgroundColor: '#a855f7', color: 'white', border: 'none', padding: '0.6rem 1.2rem', borderRadius: '0.375rem', cursor: 'pointer', width: '100%', fontWeight: '600' }}>Criar Utilizador</button>
              </form>
            </div>

            <div style={{ backgroundColor: '#0f172a', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #334155' }}>
              <h3 style={{ marginTop: 0, color: '#38bdf8' }}>Contas Registadas no Sistema</h3>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8', textAlign: 'left' }}>
                      <th style={{ padding: '0.5rem' }}>Utilizador</th>
                      <th style={{ padding: '0.5rem' }}>Privilégio</th>
                                            <th style={{ padding: '0.5rem', textAlign: 'right' }}>Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usersList.map(u => (
                      <tr key={u.username} style={{ borderBottom: '1px solid #1e293b' }}>
                        <td style={{ padding: '0.6rem', fontWeight: '500' }}>{u.username}</td>
                        <td style={{ padding: '0.6rem' }}>
                          <span style={{ padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', backgroundColor: u.role === 'admin' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(56, 189, 248, 0.2)', color: u.role === 'admin' ? '#c084fc' : '#38bdf8' }}>
                            {u.role === 'admin' ? 'Administrador' : 'Viewer (Leitura)'}
                          </span>
                        </td>
                        <td style={{ padding: '0.6rem', textAlign: 'right', display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', alignItems: 'center' }}>
                          <button onClick={() => { setEditingUser(u.username); setTargetNewPassword(''); setTargetConfirmPassword(''); setAdminAuthPassword(''); }} style={{ background: 'none', border: 'none', color: '#eab308', cursor: 'pointer' }} title="Alterar Senha">
                            <Edit3 size={16} />
                          </button>
                          {u.username !== 'admin' && (
                            <button onClick={() => handleDeleteUser(u.username)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer' }} title="Remover Utilizador">
                              <Trash2 size={16} />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        </div>
      )}
    </>
  );
}
